/* Native temperature-vector handoff. GPL-3.0-or-later, as 3D-ICE.
 * A temperature initial condition, not a solver/plugin checkpoint.
 */
#ifndef TDICE_TEMPERATURE_STATE_H
#define TDICE_TEMPERATURE_STATE_H
#include <ctype.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "thermal_data.h"

#define TDICE_TEMPERATURE_STATE_VERSION "3DICE_TEMPERATURE_STATE_V1"

static inline uint64_t temperature_state_hash_text(uint64_t hash, const char *text)
{
    for (; *text; text++)
    {
        hash ^= (unsigned char)*text;
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

/* Hash explicit fields, not padding or pointers, in native cell order.
 * Matching only the number of cells would allow a different mesh by mistake.
 * Material and power changes are allowed for a new measurement workload.
 */
static inline uint64_t temperature_state_mesh_hash(Dimensions_t *d)
{
    uint64_t hash = UINT64_C(14695981039346656037);
    char text[512];
    Quantity_t i;
    Non_uniform_cellListNode_t *node;
    snprintf(text, sizeof text, "%u %u %u %u %u %.17g %.17g\n",
        (unsigned)d->NonUniform, (unsigned)d->Grid.NLayers,
        (unsigned)d->Grid.NRows, (unsigned)d->Grid.NColumns,
        (unsigned)d->Grid.NCells, d->Chip.Length, d->Chip.Width);
    hash = temperature_state_hash_text(hash, text);
    snprintf(text, sizeof text, "%.17g %.17g %.17g %.17g %.17g %u\n",
        d->Cell.FirstWallLength, d->Cell.WallLength, d->Cell.ChannelLength,
        d->Cell.LastWallLength, d->Cell.Width, (unsigned)d->Cell.NHeights);
    hash = temperature_state_hash_text(hash, text);
    for (i = 0; i < d->Cell.NHeights; i++)
    {
        snprintf(text, sizeof text, "%.17g\n", d->Cell.Heights[i]);
        hash = temperature_state_hash_text(hash, text);
    }
    if (d->NonUniform == 1)
        for (node = d->Cell_list.First; node != NULL; node = node->Next)
        {
            Non_uniform_cell_t *c = &node->Data;
            snprintf(text, sizeof text, "%u %.17g %.17g %.17g %.17g %.17g %.17g %u\n",
                (unsigned)c->layer_info, c->left_x, c->left_y, c->left_z,
                c->length, c->width, c->height, (unsigned)c->isChannel);
            hash = temperature_state_hash_text(hash, text);
        }
    return hash;
}

static inline Error_t write_temperature_state
(const char *path, ThermalData_t *data, Dimensions_t *dimensions)
{
    Quantity_t i;
    int failed = 0;
    FILE *stream = fopen(path, "w");
    if (stream == NULL)
    {
        fprintf(stderr, "Cannot create temperature state %s\n", path);
        return TDICE_FAILURE;
    }
    fprintf(stream, "%s\n%lu %016llx\n", TDICE_TEMPERATURE_STATE_VERSION,
        (unsigned long)data->Size,
        (unsigned long long)temperature_state_mesh_hash(dimensions));
    for (i = 0; i < data->Size; i++)
    {
        if (!isfinite(data->Temperatures[i]) || data->Temperatures[i] <= 0.0)
        {
            failed = 1;
            break;
        }
        fprintf(stream, "%lu %.17g\n", (unsigned long)i, data->Temperatures[i]);
    }
    if (ferror(stream)) failed = 1;
    if (fclose(stream) != 0) failed = 1;
    if (failed)
    {
        remove(path);
        fprintf(stderr, "Cannot write valid temperature state %s\n", path);
        return TDICE_FAILURE;
    }
    return TDICE_SUCCESS;
}

static inline Error_t load_temperature_state
(const char *path, ThermalData_t *data, Dimensions_t *dimensions)
{
    char magic[64];
    unsigned long count, index;
    unsigned long long mesh_hash;
    Quantity_t i;
    int ch;
    Temperature_t *values = NULL;
    Error_t result = TDICE_FAILURE;
    FILE *stream = fopen(path, "r");
    if (stream == NULL)
    {
        fprintf(stderr, "Cannot open temperature state %s\n", path);
        return TDICE_FAILURE;
    }
    if (fscanf(stream, "%63s %lu %llx", magic, &count, &mesh_hash) != 3 ||
        strcmp(magic, TDICE_TEMPERATURE_STATE_VERSION) != 0 ||
        count != (unsigned long)data->Size ||
        mesh_hash != (unsigned long long)temperature_state_mesh_hash(dimensions))
    {
        fprintf(stderr, "Temperature state format or mesh mismatch: %s\n", path);
        goto cleanup;
    }
    values = (Temperature_t *)malloc(sizeof(*values) * data->Size);
    if (values == NULL) goto cleanup;
    for (i = 0; i < data->Size; i++)
        if (fscanf(stream, "%lu %lf", &index, &values[i]) != 2 ||
            index != (unsigned long)i || !isfinite(values[i]) || values[i] <= 0.0)
        {
            fprintf(stderr, "Invalid temperature state cell %lu: %s\n", (unsigned long)i, path);
            goto cleanup;
        }
    do { ch = fgetc(stream); } while (ch != EOF && isspace((unsigned char)ch));
    if (ch != EOF || ferror(stream))
    {
        fprintf(stderr, "Trailing data or read error in temperature state: %s\n", path);
        goto cleanup;
    }
    /* Preserve the address: SuperLU's dense RHS aliases Temperatures. */
    memcpy(data->Temperatures, values, sizeof(*values) * data->Size);
    fprintf(stdout, "Loaded full temperature state: %lu cells from %s\n", count, path);
    result = TDICE_SUCCESS;
cleanup:
    free(values);
    fclose(stream);
    return result;
}
#endif
