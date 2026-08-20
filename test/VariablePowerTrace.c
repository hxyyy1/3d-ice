/******************************************************************************
 * Regression test for variable-duration power traces.                       *
 ******************************************************************************/

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "analysis.h"
#include "output.h"
#include "power_trace.h"

static int check (int condition, const char *message)
{
    if (condition != 0)

        return 1 ;

    fprintf (stderr, "VariablePowerTrace: %s\n", message) ;

    return 0 ;
}

int main (void)
{
    Analysis_t analysis ;
    Output_t output ;
    InspectionPoint_t relative_output ;
    InspectionPoint_t absolute_output ;
    PowerTrace_t trace ;
    PowerTraceReadResult_t read_result ;
    Time_t slot_time ;
    float powers [2] ;
    FILE *stream = tmpfile ( ) ;
    char directory_template [] = "/tmp/3dice-output-test-XXXXXX" ;
    char expected_path [1024] ;
    struct stat directory_info ;

    if (check (stream != NULL, "cannot create temporary trace") == 0)

        return 1 ;

    fputs ("dt core cache\n0.005 10 3\n0.015 12 4.2\n", stream) ;
    rewind (stream) ;

    if (check
        (power_trace_init (&trace, stream, 2u, 0, 1u) == TDICE_SUCCESS,
         "cannot parse dt header") == 0 ||
        check (power_trace_has_variable_slot_time (&trace) == true,
         "dt header was not detected") == 0)

        return 1 ;

    read_result = power_trace_read_slot (&trace, &slot_time, powers) ;

    if (check (read_result == TDICE_POWER_TRACE_READ_SLOT,
         "cannot read first slot") == 0 ||
        check (fabs (slot_time - 0.005) < 1.0e-12,
         "wrong first duration") == 0 ||
        check (powers [0] == 10.0f && powers [1] == 3.0f,
         "wrong first power row") == 0)

        return 1 ;

    read_result = power_trace_read_slot (&trace, &slot_time, powers) ;

    if (check (read_result == TDICE_POWER_TRACE_READ_SLOT,
         "cannot read second slot") == 0 ||
        check (fabs (slot_time - 0.015) < 1.0e-12,
         "wrong second duration") == 0 ||
        check (power_trace_read_slot (&trace, &slot_time, powers) ==
         TDICE_POWER_TRACE_READ_END, "end of trace was not detected") == 0)

        return 1 ;

    fclose (stream) ;

    stream = tmpfile ( ) ;

    if (check (stream != NULL, "cannot create fixed trace") == 0)

        return 1 ;

    fputs ("core cache\n10 3\n", stream) ;
    rewind (stream) ;

    if (check
        (power_trace_init (&trace, stream, 2u, 0, 1u) == TDICE_SUCCESS,
         "cannot parse fixed-duration header") == 0 ||
        check (power_trace_has_variable_slot_time (&trace) == false,
         "fixed trace was detected as variable") == 0 ||
        check (power_trace_read_slot (&trace, &slot_time, powers) ==
         TDICE_POWER_TRACE_READ_SLOT, "cannot read fixed-duration slot") == 0 ||
        check (powers [0] == 10.0f && powers [1] == 3.0f,
         "wrong fixed-duration power row") == 0)

        return 1 ;

    fclose (stream) ;

    analysis_init (&analysis) ;
    analysis.AnalysisType = TDICE_ANALYSIS_TYPE_TRANSIENT ;
    analysis.StepTime = 0.005 ;
    analysis.SlotTime = 0.01 ;
    analysis.SlotLength = 2u ;

    increase_by_step_time (&analysis) ;
    increase_by_step_time (&analysis) ;

    if (check (analysis.VariableStepMode == 0,
         "fixed analysis unexpectedly entered variable mode") == 0 ||
        check (analysis.CurrentTime == 2u && analysis.CurrentSlot == 1u,
         "fixed step/slot progression changed") == 0 ||
        check (fabs (get_simulated_time (&analysis) - 0.01) < 1.0e-12,
         "fixed-step accumulated time changed") == 0)

        return 1 ;

    analysis_init (&analysis) ;
    analysis.AnalysisType = TDICE_ANALYSIS_TYPE_TRANSIENT ;
    analysis.StepTime = 0.005 ;

    if (check
        (analysis_set_variable_step_time (&analysis, 0.005) == TDICE_SUCCESS,
         "cannot set first variable step") == 0 ||
        check (slot_completed (&analysis) == true,
         "initial slot boundary was not detected") == 0)

        return 1 ;

    increase_by_step_time (&analysis) ;

    if (check (analysis.CurrentSlot == 1u && slot_completed (&analysis) == true,
         "one-step slot did not complete") == 0 ||
        check
        (analysis_set_variable_step_time (&analysis, 0.015) == TDICE_SUCCESS,
         "cannot set second variable step") == 0)

        return 1 ;

    increase_by_step_time (&analysis) ;

    if (check (analysis.CurrentSlot == 2u && slot_completed (&analysis) == true,
         "second variable step did not complete") == 0 ||
        check (analysis.CurrentTime == 2u,
         "a dt row performed more than one solver step") == 0 ||
        check (fabs (get_simulated_time (&analysis) - 0.02) < 1.0e-12,
         "accumulated time is not 0.02 seconds") == 0 ||
        check
        (analysis_set_variable_step_time (&analysis, 0.007) == TDICE_SUCCESS,
         "arbitrary positive dt was rejected") == 0 ||
        check
        (analysis_set_variable_step_time (&analysis, 0.0) == TDICE_FAILURE,
         "zero dt was accepted") == 0)

        return 1 ;

    output_init (&output) ;
    inspection_point_init (&relative_output) ;
    inspection_point_init (&absolute_output) ;

    relative_output.Instant = TDICE_OUTPUT_INSTANT_SLOT ;
    absolute_output.Instant = TDICE_OUTPUT_INSTANT_FINAL ;
    string_copy_cstr (&relative_output.FileName, "nested/temperature.txt") ;
    string_copy_cstr (&absolute_output.FileName, "/tmp/absolute-temperature.txt") ;
    add_inspection_point (&output, &relative_output) ;
    add_inspection_point (&output, &absolute_output) ;
    inspection_point_destroy (&relative_output) ;
    inspection_point_destroy (&absolute_output) ;

    if (check (mkdtemp (directory_template) != NULL,
         "cannot create output-directory fixture") == 0 ||
        check (output_set_directory (&output, directory_template) ==
         TDICE_SUCCESS, "cannot relocate output paths") == 0)

        return 1 ;

    snprintf (expected_path, sizeof (expected_path), "%s/nested/temperature.txt",
        directory_template) ;

    if (check (strcmp
        (inspection_point_list_data
         (inspection_point_list_begin (&output.InspectionPointListSlot))->FileName,
         expected_path) == 0, "relative output path was not relocated") == 0 ||
        check (strcmp
        (inspection_point_list_data
         (inspection_point_list_begin (&output.InspectionPointListFinal))->FileName,
         "/tmp/absolute-temperature.txt") == 0,
         "absolute output path was changed") == 0)

        return 1 ;

    snprintf (expected_path, sizeof (expected_path), "%s/nested",
        directory_template) ;

    if (check (stat (expected_path, &directory_info) == 0 &&
         S_ISDIR (directory_info.st_mode),
         "relative output subdirectory was not created") == 0)

        return 1 ;

    output_destroy (&output) ;
    rmdir (expected_path) ;
    rmdir (directory_template) ;

    return 0 ;
}
