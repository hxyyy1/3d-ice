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

#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "stack_file_parser.h"

#include "stack_description.h"
#include "thermal_data.h"
#include "temperature_state.h"
#include "output.h"
#include "analysis.h"

#include <sys/resource.h>
#include <sys/time.h>

static int valid_result_suffix (const char *suffix)
{
    if (suffix == NULL)

        return 0 ;

    for ( ; *suffix != '\0' ; suffix++)
    {
        if ((*suffix < 'A' || *suffix > 'Z') &&
            (*suffix < 'a' || *suffix > 'z') &&
            (*suffix < '0' || *suffix > '9') &&
            *suffix != '_' && *suffix != '-')

            return 0 ;
    }

    return 1 ;
}

static char *result_path
(
    const char *directory,
    const char *stem,
    const char *suffix,
    const char *extension
)
{
    size_t length = strlen (directory) + strlen (stem) + strlen (suffix) +
        strlen (extension) + 2u ;
    char *path = (char *) malloc (length) ;

    if (path != NULL)

        snprintf (path, length, "%s/%s%s%s", directory, stem, suffix, extension) ;

    return path ;
}

static Temperature_t average_layer_temperature
(
    ThermalData_t *tdata,
    Dimensions_t  *dimensions,
    CellIndex_t    layer
)
{
    Temperature_t sum = 0.0 ;
    Quantity_t count = 0u ;

    if (dimensions->NonUniform == 1)
    {
        Quantity_t temperature_index = 0u ;
        Non_uniform_cellListNode_t *cell ;

        for (cell = dimensions->Cell_list.First ; cell != NULL ;
             cell = cell->Next, temperature_index++)
        {
            if (cell->Data.layer_info == layer)
            {
                sum += tdata->Temperatures [temperature_index] ;
                count++ ;
            }
        }
    }
    else
    {
        CellIndex_t row, column ;

        for (row = first_row (dimensions) ; row <= last_row (dimensions) ; row++)

            for (column = first_column (dimensions) ;
                 column <= last_column (dimensions) ; column++)
            {
                sum += tdata->Temperatures [get_cell_offset_in_stack
                    (dimensions, layer, row, column)] ;
                count++ ;
            }
    }

    return count == 0u ? 0.0 : sum / count ;
}

static Error_t write_steady_nodes
(
    FILE          *stream,
    ThermalData_t *tdata,
    Dimensions_t  *dimensions
)
{
    CellIndex_t layer ;

    for (layer = first_layer (dimensions) ; layer <= last_layer (dimensions) ; layer++)
    {
        Floorplan_t *floorplan = tdata->PowerGrid.FloorplansProfile [layer] ;

        if (floorplan == NULL)
        {
            fprintf (stream, "layer_%u_average\t%.12g\n",
                (unsigned int) layer,
                average_layer_temperature (tdata, dimensions, layer)) ;

            continue ;
        }

        Quantity_t element_count = 0u ;
        Temperature_t *layer_temperatures = tdata->Temperatures ;
        Temperature_t *averages ;
        FloorplanElementListNode_t *node ;
        Quantity_t index = 0u ;

        if (dimensions->NonUniform != 1)

            layer_temperatures += get_cell_offset_in_stack
                (dimensions, layer, first_row (dimensions), first_column (dimensions)) ;

        averages = get_all_avg_temperatures_floorplan
            (floorplan, dimensions, layer_temperatures, &element_count, NULL) ;

        if (averages == NULL)

            return TDICE_FAILURE ;

        for (node = floorplan_element_list_begin (&floorplan->ElementsList) ;
             node != NULL ; node = floorplan_element_list_next (node), index++)
        {
            FloorplanElement_t *element = floorplan_element_list_data (node) ;

            if (index == element_count)

                break ;

            fprintf (stream, "layer_%u_%s\t%.12g\n",
                (unsigned int) layer, element->Id, averages [index]) ;
        }

        free (averages) ;
    }

    return ferror (stream) == 0 ? TDICE_SUCCESS : TDICE_FAILURE ;
}

static Error_t write_steady_grid
(
    FILE          *stream,
    ThermalData_t *tdata,
    Dimensions_t  *dimensions
)
{
    CellIndex_t layer ;

    for (layer = first_layer (dimensions) ; layer <= last_layer (dimensions) ; layer++)
    {
        Quantity_t local_index = 0u ;

        fprintf (stream, "Layer %u:\n", (unsigned int) layer) ;

        if (dimensions->NonUniform == 1)
        {
            Quantity_t temperature_index = 0u ;
            Non_uniform_cellListNode_t *cell ;

            for (cell = dimensions->Cell_list.First ; cell != NULL ;
                 cell = cell->Next, temperature_index++)
            {
                if (cell->Data.layer_info == layer)

                    fprintf (stream, "%u\t%.12g\n", (unsigned int) local_index++,
                        tdata->Temperatures [temperature_index]) ;
            }
        }
        else
        {
            CellIndex_t row, column ;

            for (row = first_row (dimensions) ; row <= last_row (dimensions) ; row++)

                for (column = first_column (dimensions) ;
                     column <= last_column (dimensions) ; column++)
                {
                    fprintf (stream, "%u\t%.12g\n", (unsigned int) local_index++,
                        tdata->Temperatures [get_cell_offset_in_stack
                            (dimensions, layer, row, column)]) ;
                }
        }
    }

    return ferror (stream) == 0 ? TDICE_SUCCESS : TDICE_FAILURE ;
}

static Error_t export_steady_results
(
    const char    *directory,
    const char    *suffix,
    ThermalData_t *tdata,
    Dimensions_t  *dimensions
)
{
    char *node_path = result_path (directory, "temperature", suffix, ".steady") ;
    char *grid_path = result_path
        (directory, "temperature_grid", suffix, ".steady") ;
    FILE *node_stream ;
    FILE *grid_stream ;
    Error_t result = TDICE_FAILURE ;

    if (node_path == NULL || grid_path == NULL)

        goto cleanup ;

    node_stream = fopen (node_path, "w") ;
    grid_stream = fopen (grid_path, "w") ;

    if (node_stream == NULL || grid_stream == NULL)
    {
        fprintf (stderr, "Cannot create standardized steady result files\n") ;

        if (node_stream != NULL) fclose (node_stream) ;
        if (grid_stream != NULL) fclose (grid_stream) ;

        goto cleanup ;
    }

    result = write_steady_nodes (node_stream, tdata, dimensions) ;

    if (write_steady_grid (grid_stream, tdata, dimensions) != TDICE_SUCCESS)

        result = TDICE_FAILURE ;

    fclose (node_stream) ;
    fclose (grid_stream) ;

cleanup :
    free (node_path) ;
    free (grid_path) ;

    return result ;
}

int main(int argc, char** argv)
{
    StackDescription_t stkd ;
    Analysis_t         analysis ;
    Output_t           output ;
    ThermalData_t      tdata ;

    SimResult_t (*emulate) (ThermalData_t*, Dimensions_t*, Analysis_t*) ;
    ///  Pointer to function

    Error_t error ;

    // Checks if there are the all the arguments
    ////////////////////////////////////////////////////////////////////////////

#define EXE_NAME     argv[0]
#define STK_FILE     argv[1]

    char *temperature_state_file = NULL ;
    char *steady_results_dir = NULL ;
    char *result_suffix = (char *) "" ;
    int arg_index ;

    if (argc == 2 && strcmp(argv[1], "--temperature-state-version") == 0)
    {
        puts(TDICE_TEMPERATURE_STATE_VERSION);
        return EXIT_SUCCESS;
    }

    if (argc < 2)
    {
        fprintf(stderr,
            "Usage: \"%s file.stk [--steady-results-dir directory] "
            "[--result-suffix suffix] [--temperature-state-file file]\"\n", EXE_NAME) ;
        return EXIT_FAILURE ;
    }

    for (arg_index = 2 ; arg_index < argc ; arg_index++)
    {
        if (strcmp (argv [arg_index], "--steady-results-dir") == 0)
        {
            if (++arg_index == argc)
            {
                fprintf (stderr, "--steady-results-dir requires a directory\n") ;

                return EXIT_FAILURE ;
            }

            steady_results_dir = argv [arg_index] ;
        }
        else if (strcmp(argv[arg_index], "--temperature-state-file") == 0)
        {
            if (++arg_index == argc || argv[arg_index][0] == '\0')
            {
                fprintf(stderr, "--temperature-state-file requires a path\n");
                return EXIT_FAILURE;
            }
            temperature_state_file = argv[arg_index];
        }
        else if (strcmp (argv [arg_index], "--result-suffix") == 0)
        {
            if (++arg_index == argc || valid_result_suffix (argv [arg_index]) == 0)
            {
                fprintf (stderr, "--result-suffix contains invalid characters\n") ;

                return EXIT_FAILURE ;
            }

            result_suffix = argv [arg_index] ;
        }
        else
        {
            fprintf (stderr, "Unknown emulator option %s\n", argv [arg_index]) ;

            return EXIT_FAILURE ;
        }
    }

    // Init StackDescription and parse the input file
    ////////////////////////////////////////////////////////////////////////////
    clock_t Time_0 = clock() ;
    fprintf (stdout, "Preparing stk data ... ") ; fflush (stdout) ;
    
    // test for time
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);


    stack_description_init (&stkd) ;
    analysis_init          (&analysis) ;
    output_init            (&output) ;

    error = parse_stack_description_file (STK_FILE, &stkd, &analysis, &output) ;

    if (error != TDICE_SUCCESS)    return EXIT_FAILURE ;

    if (analysis.AnalysisType == TDICE_ANALYSIS_TYPE_TRANSIENT)

        emulate = &emulate_step ;

    else if (analysis.AnalysisType == TDICE_ANALYSIS_TYPE_STEADY)

        emulate = &emulate_steady ;

    else
    {
        fprintf (stderr, "unknown analysis type!\n ");

        stack_description_destroy (&stkd) ;
        output_destroy            (&output) ;

        return EXIT_FAILURE ;
    }

    if (steady_results_dir != NULL || temperature_state_file != NULL)
    {
        if (analysis.AnalysisType != TDICE_ANALYSIS_TYPE_STEADY)
        {
            fprintf (stderr, "steady result/state export requires a steady analysis\n") ;

            stack_description_destroy (&stkd) ;
            output_destroy            (&output) ;

            return EXIT_FAILURE ;
        }

    }

    //fprintf (stdout, "done !\n") ;

    fprintf (stdout, "\nRead in configuration files took %.3f sec\n",
        ( (double)clock() - Time_0 ) / CLOCKS_PER_SEC ) ;
    // Generate output files
    ////////////////////////////////////////////////////////////////////////////

    // We use "% " as prefix for matlab compatibility (header will be a comment)

    error = generate_output_headers (&output, stkd.Dimensions, (String_t)"% ") ;

    if (error != TDICE_SUCCESS)
    {
        fprintf (stderr, "error in initializing output files \n ");

        stack_description_destroy (&stkd) ;
        output_destroy            (&output) ;

        return EXIT_FAILURE ;
    }

    // Init thermal data and fill it using the StackDescription
    ////////////////////////////////////////////////////////////////////////////

    fprintf (stdout, "\nPreparing thermal data ... ") ; fflush (stdout) ;

    thermal_data_init (&tdata) ;

    error = thermal_data_build

        (&tdata, &stkd.StackElements, stkd.Dimensions, &analysis, &stkd.Materials) ;


    if (error != TDICE_SUCCESS)
    {
        stack_description_destroy (&stkd) ;
        output_destroy            (&output) ;

        return EXIT_FAILURE ;
    }

    // Run the simulation and print the output
    ////////////////////////////////////////////////////////////////////////////

    SimResult_t sim_result ;

    do
    {
        sim_result = emulate (&tdata, stkd.Dimensions, &analysis) ;

        // printf("Temperature grid info:\n");
        // for(CellIndex_t i = 0; i < stkd.Dimensions->Grid.NCells; i++)
        //     printf("%d:\t%f\n", i, *(tdata.Temperatures+i));

        // New output part 1/2
        int bar_len = 30;
        char s1[31] = "------------------------------";
        char s2[31] = "                              ";
        int time_cur;
        int slot_cur;
        float scale_factor = (float) bar_len / (float) analysis.SlotLength;;

        if (sim_result == TDICE_STEP_DONE || sim_result == TDICE_SLOT_DONE)
        {
            // New output part 2/2
            time_cur = analysis.CurrentSlotStep * scale_factor;
            if (sim_result == TDICE_SLOT_DONE)
                 time_cur = bar_len;
            slot_cur = analysis.CurrentSlot +
                (sim_result == TDICE_SLOT_DONE ? 0u : 1u) ;
            fprintf(stderr, "Time slot %d: |%.*s>%.*s| %.3fs\r", slot_cur, time_cur, s1, bar_len-time_cur, s2, analysis.CurrentTime*analysis.StepTime);
            fflush(stderr);  //< Flush the output (just in case)

            // Original ouput
            // fprintf (stdout, "%.3f ", get_simulated_time (&analysis)) ;

            // fflush (stdout) ;

            generate_output (&output, stkd.Dimensions,
                             tdata.Temperatures, tdata.PowerGrid.Sources,
                             get_simulated_time (&analysis),
                             analysis.CurrentTime,
                             analysis.CurrentSlot,
                             TDICE_OUTPUT_INSTANT_STEP) ;
        }

        if (sim_result == TDICE_SLOT_DONE)
        {
            fprintf (stdout, "\n") ;

            generate_output (&output, stkd.Dimensions,
                             tdata.Temperatures, tdata.PowerGrid.Sources,
                             get_simulated_time (&analysis),
                             analysis.CurrentTime,
                             analysis.CurrentSlot,
                             TDICE_OUTPUT_INSTANT_SLOT) ;
        }

    } while (sim_result != TDICE_END_OF_SIMULATION && sim_result != TDICE_SOLVER_ERROR) ;

    if (sim_result == TDICE_SOLVER_ERROR ||
        (temperature_state_file != NULL && write_temperature_state
         (temperature_state_file, &tdata, stkd.Dimensions) != TDICE_SUCCESS))
    {
        thermal_data_destroy(&tdata);
        stack_description_destroy(&stkd);
        output_destroy(&output);
        return EXIT_FAILURE;
    }

    generate_output (&output, stkd.Dimensions,
                     tdata.Temperatures, tdata.PowerGrid.Sources,
                     get_simulated_time (&analysis),
                     analysis.CurrentTime,
                     analysis.CurrentSlot,
                     TDICE_OUTPUT_INSTANT_FINAL) ;

    if (steady_results_dir != NULL &&
        export_steady_results
        (steady_results_dir, result_suffix, &tdata, stkd.Dimensions) != TDICE_SUCCESS)
    {
        fprintf (stderr, "Cannot export standardized steady results\n") ;

        thermal_data_destroy      (&tdata) ;
        stack_description_destroy (&stkd) ;
        output_destroy            (&output) ;

        return EXIT_FAILURE ;
    }

    /// Present time consumption for test
    clock_gettime(CLOCK_MONOTONIC, &end);
    fprintf (stdout, "\nEmulation took %.3f sec\n",
        (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9 ) ;

    // Output the maximum memory usage
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
        // ru_maxrss is in kilobytes on Linux
        long usage_kb = usage.ru_maxrss;
        if (usage_kb < 1024) {
            printf("Peak memory usage: %ld KB\n", usage_kb);
        } else if (usage_kb < 1024 * 1024) {
            printf("Peak memory usage: %.2f MB\n", usage_kb / 1024.0);
        } else {
            printf("Peak memory usage: %.2f GB\n", usage_kb / (1024.0 * 1024.0));
        }
    } else {
        perror("getrusage failed");
    }
    // free all data
    ////////////////////////////////////////////////////////////////////////////

    thermal_data_destroy      (&tdata) ;
    stack_description_destroy (&stkd) ;
    output_destroy            (&output) ;

    return EXIT_SUCCESS ;
}
