/******************************************************************************
 * This file is part of 3D-ICE, version 4.0 .                                 *
 ******************************************************************************/

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <strings.h>
#include <unistd.h>

#include "power_trace.h"

#define POWER_TRACE_TOKEN_LENGTH 256u

static int read_token (PowerTrace_t *trace, char token [POWER_TRACE_TOKEN_LENGTH])
{
    int waiting = 0 ;

    for ( ; ; )
    {
        int result = fscanf (trace->Stream, "%255s", token) ;

        if (result == 1)

            return 1 ;

        if (result == EOF && trace->Follow != 0)
        {
            if (waiting == 0)
            {
                fprintf (stdout,
                    "Waiting for power trace values for slot %u ...\n",
                    (unsigned int) trace->SlotIndex) ;
                fflush (stdout) ;
                waiting = 1 ;
            }

            clearerr (trace->Stream) ;
            sleep (trace->PollSeconds) ;

            continue ;
        }

        return 0 ;
    }
}

static int parse_time (char *token, Time_t *value)
{
    char *end ;

    errno = 0 ;
    *value = strtod (token, &end) ;

    return errno != ERANGE && end != token && *end == '\0' &&
           isfinite (*value) != 0 ;
}

static int parse_power (char *token, float *value)
{
    char *end ;

    errno = 0 ;
    *value = strtof (token, &end) ;

    return errno != ERANGE && end != token && *end == '\0' &&
           isfinite (*value) != 0 ;
}

Error_t power_trace_init
(
    PowerTrace_t *trace,
    FILE         *stream,
    Quantity_t    nelements,
    int           follow,
    unsigned int  poll_seconds
)
{
    char token [POWER_TRACE_TOKEN_LENGTH] ;
    Quantity_t index ;

    trace->Stream              = stream ;
    trace->NElements           = nelements ;
    trace->SlotIndex           = 0u ;
    trace->Follow              = follow ;
    trace->PollSeconds         = poll_seconds ;
    trace->HasVariableSlotTime = 0 ;
    trace->HasPendingPower     = 0 ;
    trace->PendingPower        = 0.0f ;

    if (stream == NULL || nelements == 0u || poll_seconds == 0u ||
        read_token (trace, token) == 0)
    {
        fprintf (stderr, "Power trace is empty or unavailable\n") ;

        return TDICE_FAILURE ;
    }

    if (strcasecmp (token, "dt") == 0)
    {
        trace->HasVariableSlotTime = 1 ;

        for (index = 0u ; index != nelements ; index++)
        {
            if (read_token (trace, token) == 0)
            {
                fprintf (stderr,
                    "Power trace header has fewer than %u power columns\n",
                    (unsigned int) nelements) ;

                return TDICE_FAILURE ;
            }
        }

        return TDICE_SUCCESS ;
    }

    if (parse_power (token, &trace->PendingPower) != 0)
    {
        trace->HasPendingPower = 1 ;

        return TDICE_SUCCESS ;
    }

    for (index = 1u ; index != nelements ; index++)
    {
        if (read_token (trace, token) == 0)
        {
            fprintf (stderr,
                "Power trace header has fewer than %u power columns\n",
                (unsigned int) nelements) ;

            return TDICE_FAILURE ;
        }
    }

    return TDICE_SUCCESS ;
}

PowerTraceReadResult_t power_trace_read_slot
(
    PowerTrace_t *trace,
    Time_t       *slot_time,
    float        *powers
)
{
    char token [POWER_TRACE_TOKEN_LENGTH] ;
    Quantity_t index = 0u ;

    *slot_time = 0.0 ;

    if (trace->HasVariableSlotTime != 0)
    {
        if (read_token (trace, token) == 0)

            return TDICE_POWER_TRACE_READ_END ;

        if (parse_time (token, slot_time) == 0)
        {
            fprintf (stderr, "Invalid dt '%s' in power trace slot %u\n",
                token, (unsigned int) trace->SlotIndex) ;

            return TDICE_POWER_TRACE_READ_ERROR ;
        }
    }

    if (trace->HasPendingPower != 0)
    {
        powers [index++] = trace->PendingPower ;
        trace->HasPendingPower = 0 ;
    }

    for ( ; index != trace->NElements ; index++)
    {
        if (read_token (trace, token) == 0)
        {
            if (index == 0u && trace->HasVariableSlotTime == 0)

                return TDICE_POWER_TRACE_READ_END ;

            fprintf (stderr,
                "Incomplete power trace slot %u: missing element %u\n",
                (unsigned int) trace->SlotIndex, (unsigned int) index) ;

            return TDICE_POWER_TRACE_READ_ERROR ;
        }

        if (parse_power (token, &powers [index]) == 0)
        {
            fprintf (stderr,
                "Invalid power '%s' in slot %u, element %u\n",
                token, (unsigned int) trace->SlotIndex, (unsigned int) index) ;

            return TDICE_POWER_TRACE_READ_ERROR ;
        }
    }

    trace->SlotIndex++ ;

    return TDICE_POWER_TRACE_READ_SLOT ;
}

bool power_trace_has_variable_slot_time (PowerTrace_t *trace)
{
    return trace->HasVariableSlotTime != 0 ;
}
