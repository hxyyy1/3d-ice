/* Full-precision thermal regression; output is native double temperature
   vectors after every slot (all cells, including passive/fluid layers).
   Usage: ThermalCleanupRegression stack output fixed|variable|steady steps
   Optional: actual variable-dt power trace as the sixth argument. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stack_file_parser.h"
#include "stack_description.h"
#include "thermal_data.h"
#include "analysis.h"
#include "output.h"
#include "power_trace.h"

int main(int argc, char **argv)
{
    assert(argc == 5 || argc == 6);
    StackDescription_t stkd;
    Analysis_t analysis;
    Output_t output;
    ThermalData_t tdata;
    stack_description_init(&stkd);
    analysis_init(&analysis);
    output_init(&output);
    thermal_data_init(&tdata);
    assert(parse_stack_description_file(argv[1], &stkd, &analysis, &output) == 0);
    const char *threads = getenv("ICE_TEST_THREADS");
    analysis.NumOfCores = threads ? atoi(threads) : 1;
    assert(thermal_data_build(&tdata, &stkd.StackElements, stkd.Dimensions,
                              &analysis, &stkd.Materials) == TDICE_SUCCESS);
    FILE *out = fopen(argv[2], "wb");
    assert(out);
    FILE *input = argc == 6 ? fopen(argv[5], "r") : NULL;
    PowerTrace_t trace;
    Quantity_t n = get_total_number_of_floorplan_elements(&stkd);
    float *powers = calloc(n, sizeof(*powers));
    assert(powers);
    if (argc == 6) {
        assert(input);
        assert(power_trace_init(&trace, input, n, 0, 1) == TDICE_SUCCESS);
    }
    double times[] = {0.00001, 0.005, 0.005, 0.0002, 0.015, 0.00001};
    int steps = atoi(argv[4]);
    for (int step = 0; step < steps; ++step) {
        Time_t dt = times[step % 6];
        if (input) {
            assert(power_trace_read_slot(&trace, &dt, powers) == TDICE_POWER_TRACE_READ_SLOT);
            PowersQueue_t queue;
            powers_queue_init(&queue);
            powers_queue_build(&queue, n);
            for (Quantity_t i = 0; i < n; ++i) put_into_powers_queue(&queue, powers[i]);
            assert(insert_power_values(&tdata.PowerGrid, &queue) == TDICE_SUCCESS);
            powers_queue_destroy(&queue);
        }
        if (strcmp(argv[3], "variable") == 0) {
            double old_dt = analysis.StepTime;
            void *old_l = tdata.SM_A.SLUMatrix_L.Store;
            assert(thermal_data_set_variable_step(&tdata, stkd.Dimensions, &analysis, -1) == TDICE_FAILURE);
            assert(thermal_data_set_variable_step(&tdata, stkd.Dimensions, &analysis, NAN) == TDICE_FAILURE);
            assert(analysis.StepTime == old_dt && tdata.SM_A.SLUMatrix_L.Store == old_l);
            assert(thermal_data_set_variable_step(&tdata, stkd.Dimensions, &analysis, dt) == TDICE_SUCCESS);
            if (old_dt == dt) assert(tdata.SM_A.SLUMatrix_L.Store == old_l);
        }
        SimResult_t result = strcmp(argv[3], "steady") == 0
            ? emulate_steady(&tdata, stkd.Dimensions, &analysis)
            : emulate_slot(&tdata, stkd.Dimensions, &analysis);
        assert(result == (strcmp(argv[3], "steady") == 0 ? TDICE_END_OF_SIMULATION : TDICE_SLOT_DONE));
        for (CellIndex_t i = 0; i < tdata.Size; ++i) assert(isfinite(tdata.Temperatures[i]));
        assert(fwrite(tdata.Temperatures, sizeof(double), tdata.Size, out) == tdata.Size);
    }
    printf("REGRESSION cells=%u steps=%d\n", tdata.Size, steps);
    free(powers);
    if (input) fclose(input);
    fclose(out);
    thermal_data_destroy(&tdata);
    stack_description_destroy(&stkd);
    output_destroy(&output);
    return 0;
}
