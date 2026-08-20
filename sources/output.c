/******************************************************************************
 * This file is part of 3D-ICE, version 4.0 .                                 *
 *                                                                            *
 * 3D-ICE is free software: you can  redistribute it and/or  modify it  under *
 * the terms of the  GNU General  Public  License as  published by  the  Free *
 * Software  Foundation, either  version  3  of  the License,  or  any  later *
 * version.                                                                   *
 *                                                                            *
 * 3D-ICE is  distributed  in the hope  that it will  be useful, but  WITHOUT *
 * ANY  WARRANTY; without  even the  implied warranty  of MERCHANTABILITY  or *
 * FITNESS  FOR A PARTICULAR  PURPOSE. See the GNU General Public License for *
 * more details.                                                              *
 *                                                                            *
 * You should have  received a copy of  the GNU General  Public License along *
 * with 3D-ICE. If not, see <http://www.gnu.org/licenses/>.                   *
 *                                                                            *
 *                             Copyright (C) 2021                             *
 *   Embedded Systems Laboratory - Ecole Polytechnique Federale de Lausanne   *
 *                            All Rights Reserved.                            *
 *                                                                            *
 * Authors: Arvind Sridhar              Alessandro Vincenzi                   *
 *          Giseong Bak                 Martino Ruggiero                      *
 *          Thomas Brunschwiler         Eder Zulian                           *
 *          Federico Terraneo           Darong Huang                          *
 *          Kai Zhu                     Luis Costero                          *
 *          Marina Zapater              David Atienza                         *
 *                                                                            *
 * For any comment, suggestion or request  about 3D-ICE, please  register and *
 * write to the mailing list (see http://listes.epfl.ch/doc.cgi?liste=3d-ice) *
 * Any usage  of 3D-ICE  for research,  commercial or other  purposes must be *
 * properly acknowledged in the resulting products or publications.           *
 *                                                                            *
 * EPFL-STI-IEL-ESL                     Mail : 3d-ice@listes.epfl.ch          *
 * Batiment ELG, ELG 130                       (SUBSCRIPTION IS NECESSARY)    *
 * Station 11                                                                 *
 * 1015 Lausanne, Switzerland           Url  : http://esl.epfl.ch/3d-ice      *
 ******************************************************************************/

#include <errno.h>
#include <stdlib.h> // For the memory functions malloc/free
#include <string.h> // For strlen
#include <sys/stat.h>

#include "output.h"

/******************************************************************************/

void output_init (Output_t *output)
{
    inspection_point_list_init (&output->InspectionPointListFinal) ;
    inspection_point_list_init (&output->InspectionPointListSlot) ;
    inspection_point_list_init (&output->InspectionPointListStep) ;
}

/******************************************************************************/

void output_copy (Output_t *dst, Output_t *src)
{
    output_destroy (dst) ;

    inspection_point_list_copy

        (&dst->InspectionPointListFinal, &src->InspectionPointListFinal) ;

    inspection_point_list_copy

        (&dst->InspectionPointListSlot, &src->InspectionPointListSlot) ;

    inspection_point_list_copy

        (&dst->InspectionPointListStep, &src->InspectionPointListStep) ;
}

/******************************************************************************/

void output_destroy (Output_t *output)
{
    inspection_point_list_destroy (&output->InspectionPointListFinal) ;
    inspection_point_list_destroy (&output->InspectionPointListSlot) ;
    inspection_point_list_destroy (&output->InspectionPointListStep) ;

    output_init (output) ;
}

/******************************************************************************/

static Error_t ensure_directory (String_t directory)
{
    struct stat info ;

    if (mkdir (directory, 0777) == 0)

        return TDICE_SUCCESS ;

    if (errno == EEXIST && stat (directory, &info) == 0 &&
        S_ISDIR (info.st_mode))

        return TDICE_SUCCESS ;

    fprintf (stderr, "Cannot create output directory %s: %s\n",
        directory, strerror (errno)) ;

    return TDICE_FAILURE ;
}

static Error_t ensure_directory_tree (String_t directory)
{
    char *path ;
    char *cursor ;
    Error_t result = TDICE_SUCCESS ;

    if (directory == NULL || directory [0] == '\0')

        return TDICE_FAILURE ;

    path = strdup (directory) ;

    if (path == NULL)

        return TDICE_FAILURE ;

    for (cursor = path + 1 ; *cursor != '\0' ; cursor++)
    {
        if (*cursor != '/')

            continue ;

        *cursor = '\0' ;

        if (ensure_directory (path) != TDICE_SUCCESS)
        {
            result = TDICE_FAILURE ;

            break ;
        }

        *cursor = '/' ;
    }

    if (result == TDICE_SUCCESS)

        result = ensure_directory (path) ;

    free (path) ;

    return result ;
}

static Error_t relocate_output_list
(
    InspectionPointList_t *list,
    String_t               directory
)
{
    InspectionPointListNode_t *node ;
    size_t directory_length = strlen (directory) ;
    int add_separator = directory [directory_length - 1u] != '/' ;

    for (node  = inspection_point_list_begin (list) ;
         node != NULL ;
         node  = inspection_point_list_next (node))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (node) ;
        char *new_name ;
        char *last_separator ;
        size_t name_length ;

        if (ipoint->FileName == NULL || ipoint->FileName [0] == '\0' ||
            ipoint->FileName [0] == '/')

            continue ;

        name_length = directory_length + (size_t) add_separator +
            strlen (ipoint->FileName) + 1u ;
        new_name = (char *) malloc (name_length) ;

        if (new_name == NULL)

            return TDICE_FAILURE ;

        snprintf (new_name, name_length, "%s%s%s", directory,
            add_separator != 0 ? "/" : "", ipoint->FileName) ;

        last_separator = strrchr (new_name, '/') ;

        if (last_separator != NULL && last_separator != new_name)
        {
            *last_separator = '\0' ;

            if (ensure_directory_tree (new_name) != TDICE_SUCCESS)
            {
                free (new_name) ;

                return TDICE_FAILURE ;
            }

            *last_separator = '/' ;
        }

        string_destroy (&ipoint->FileName) ;
        ipoint->FileName = new_name ;
    }

    return TDICE_SUCCESS ;
}

Error_t output_set_directory (Output_t *output, String_t directory)
{
    if (ensure_directory_tree (directory) != TDICE_SUCCESS)

        return TDICE_FAILURE ;

    if (relocate_output_list
        (&output->InspectionPointListFinal, directory) != TDICE_SUCCESS ||
        relocate_output_list
        (&output->InspectionPointListSlot, directory) != TDICE_SUCCESS ||
        relocate_output_list
        (&output->InspectionPointListStep, directory) != TDICE_SUCCESS)

        return TDICE_FAILURE ;

    return TDICE_SUCCESS ;
}

/******************************************************************************/

Quantity_t get_number_of_inspection_points
(
    Output_t         *output,
    OutputInstant_t   instant,
    OutputType_t      type,
    OutputQuantity_t  quantity
)
{
    Quantity_t number = 0u ;

    InspectionPointList_t *list = NULL ;

    if (instant == TDICE_OUTPUT_INSTANT_FINAL)

        list = &output->InspectionPointListFinal ;

    else if (instant == TDICE_OUTPUT_INSTANT_STEP)

        list = &output->InspectionPointListStep ;

    else if (instant == TDICE_OUTPUT_INSTANT_SLOT)

        list = &output->InspectionPointListSlot ;

    else
    {
        fprintf (stderr, "Error: Wrong ipoint instant %d\n", instant) ;

        return number ;
    }

    InspectionPointListNode_t *ipn ;

    for (ipn  = inspection_point_list_begin (list) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        if (is_inspection_point (ipoint, type, quantity) == true)

            number++ ;
    }

    return number ;
}

/******************************************************************************/

void output_print (Output_t *output, FILE *stream, String_t prefix)
{
    fprintf (stream, "%soutput :\n", prefix) ;

    String_t new_prefix = (String_t) malloc (sizeof(*new_prefix) * (5 + strlen(prefix))) ;

    if (new_prefix == NULL) return ;

    sprintf (new_prefix, "%s    ", prefix) ;

    inspection_point_list_print (&output->InspectionPointListFinal, stream, new_prefix) ;

    fprintf (stream, "%s\n", prefix) ;

    inspection_point_list_print (&output->InspectionPointListSlot, stream, new_prefix) ;

    fprintf (stream, "%s\n", prefix) ;

    inspection_point_list_print (&output->InspectionPointListStep, stream, new_prefix) ;

    fprintf (stream, "%s\n", prefix) ;

    free (new_prefix) ;
}

/******************************************************************************/

void add_inspection_point (Output_t *output, InspectionPoint_t *ipoint)
{
    InspectionPointList_t *list = NULL ;

    if (ipoint->Instant == TDICE_OUTPUT_INSTANT_FINAL)

        list = &output->InspectionPointListFinal ;

    else if (ipoint->Instant == TDICE_OUTPUT_INSTANT_STEP)

        list = &output->InspectionPointListStep ;

    else if (ipoint->Instant == TDICE_OUTPUT_INSTANT_SLOT)

        list = &output->InspectionPointListSlot ;

    else
    {
        fprintf (stderr, "Error: Unset ipoint instant %d\n", ipoint->Instant) ;

        return ;
    }


    inspection_point_list_insert_end (list, ipoint) ;
}

/******************************************************************************/

Error_t generate_output_headers
(
    Output_t     *output,
    Dimensions_t *dimensions,
    String_t      prefix
)
{
    InspectionPointListNode_t *ipn ;

    for (ipn  = inspection_point_list_begin (&output->InspectionPointListFinal) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        if (generate_inspection_point_header (ipoint, dimensions, prefix) != TDICE_SUCCESS)

            return TDICE_FAILURE ;
    }

    for (ipn  = inspection_point_list_begin (&output->InspectionPointListSlot) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        if (generate_inspection_point_header (ipoint, dimensions, prefix) != TDICE_SUCCESS)

            return TDICE_FAILURE ;
    }

    for (ipn  = inspection_point_list_begin (&output->InspectionPointListStep) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        if (generate_inspection_point_header (ipoint, dimensions, prefix) != TDICE_SUCCESS)

            return TDICE_FAILURE ;
    }

    return TDICE_SUCCESS ;
}

/******************************************************************************/

Error_t generate_output
(
    Output_t        *output,
    Dimensions_t    *dimensions,
    Temperature_t   *temperatures,
    Source_t        *sources,
    Time_t           current_time,
    Quantity_t       timestep_index,
    Quantity_t       slot_index,
    OutputInstant_t  output_instant
)
{
    InspectionPointList_t *list ;

    if (output_instant == TDICE_OUTPUT_INSTANT_FINAL)

        list = &output->InspectionPointListFinal ;

    else if (output_instant == TDICE_OUTPUT_INSTANT_STEP)

        list = &output->InspectionPointListStep ;

    else if (output_instant == TDICE_OUTPUT_INSTANT_SLOT)

        list = &output->InspectionPointListSlot ;

    else
    {
        fprintf (stderr, "Error: Wrong ipoint instant %d\n", output_instant) ;

        return TDICE_FAILURE ;
    }

    InspectionPointListNode_t *ipn ;

    for (ipn  = inspection_point_list_begin (list) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        Error_t error = generate_inspection_point_output

            (ipoint, dimensions, temperatures, sources, current_time,
             timestep_index, slot_index) ;

        if (error != TDICE_SUCCESS)

            return TDICE_FAILURE ;
    }

 /*   if (output_instant == TDICE_OUTPUT_INSTANT_FINAL && dimensions->NonUniform == 1)
    {
        print_thermal_map_3D (dimensions, temperatures);
    }
*/
   return TDICE_SUCCESS ;
}

/******************************************************************************/

Error_t fill_output_message
(
    Output_t         *output,
    Dimensions_t     *dimensions,
    Temperature_t    *temperatures,
    Source_t         *sources,
    OutputInstant_t   output_instant,
    OutputType_t      output_type,
    OutputQuantity_t  output_quantity,
    NetworkMessage_t *message
)
{
    InspectionPointList_t *list ;

    if (output_instant == TDICE_OUTPUT_INSTANT_FINAL)

        list = &output->InspectionPointListFinal ;

    else if (output_instant == TDICE_OUTPUT_INSTANT_STEP)

        list = &output->InspectionPointListStep ;

    else if (output_instant == TDICE_OUTPUT_INSTANT_SLOT)

        list = &output->InspectionPointListSlot ;

    else
    {
        fprintf (stderr, "Error: Wrong ipoint instant %d\n", output_instant) ;

        return TDICE_FAILURE ;
    }

    InspectionPointListNode_t *ipn ;

    for (ipn  = inspection_point_list_begin (list) ;
         ipn != NULL ;
         ipn  = inspection_point_list_next (ipn))
    {
        InspectionPoint_t *ipoint = inspection_point_list_data (ipn) ;

        if (is_inspection_point (ipoint, output_type, output_quantity) == true)

            fill_message_inspection_point

                (ipoint, output_quantity, dimensions, temperatures, sources, message) ;
    }

   return TDICE_SUCCESS ;
}

/******************************************************************************/
