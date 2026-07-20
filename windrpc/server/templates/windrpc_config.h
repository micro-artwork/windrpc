#ifndef WINDRPC_CONFIG_H
#define WINDRPC_CONFIG_H

#include "windrpc_common.h"

#define WINDRPC_REQUEST_ID_TYPE WINDRPC_REQUEST_ID_TYPE_NONE

#define WINDRPC_LOG_LEVEL LOG_LEVEL_INF

// [Default] 0: Separate rx/tx buffers (Double Buffer) for safety.
//           1: Share a single buffer for rx/tx (In-place) to save RAM.
#ifndef WINDRPC_USE_INPLACE_BUFFER
#define WINDRPC_USE_INPLACE_BUFFER 0
#endif

#endif