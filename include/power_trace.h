/******************************************************************************
 * This file is part of 3D-ICE, version 4.0 .                                 *
 ******************************************************************************/

#ifndef _3DICE_POWER_TRACE_H_
#define _3DICE_POWER_TRACE_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdio.h>

#include "types.h"

typedef enum
{
    TDICE_POWER_TRACE_READ_ERROR = -1,
    TDICE_POWER_TRACE_READ_END   = 0,
    TDICE_POWER_TRACE_READ_SLOT  = 1
} PowerTraceReadResult_t ;

typedef struct
{
    FILE        *Stream ;
    Quantity_t   NElements ;
    Quantity_t   SlotIndex ;
    int          Follow ;
    unsigned int PollSeconds ;
    int          HasVariableSlotTime ;
    int          HasPendingPower ;
    float        PendingPower ;
} PowerTrace_t ;

/*! Initializes a whitespace-separated power trace reader.
 *
 * A non-numeric first token is treated as a header. If that token is `dt`,
 * every data row must begin with its duration in seconds. Header labels are
 * informational; power columns remain in 3D-ICE floorplan order.
 */
Error_t power_trace_init
(
    PowerTrace_t *trace,
    FILE         *stream,
    Quantity_t    nelements,
    int           follow,
    unsigned int  poll_seconds
) ;

PowerTraceReadResult_t power_trace_read_slot
(
    PowerTrace_t *trace,
    Time_t       *slot_time,
    float        *powers
) ;

bool power_trace_has_variable_slot_time (PowerTrace_t *trace) ;

#ifdef __cplusplus
}
#endif

#endif /* _3DICE_POWER_TRACE_H_ */
