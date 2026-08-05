#ifndef WINDRPC_CONFIG_H
#define WINDRPC_CONFIG_H

#include "windrpc_common.h"

#define WINDRPC_LOG_LEVEL LOG_LEVEL_INF

// 0: Double Buffer (safe), 1: In-place Buffer (saves RAM)
#ifndef WINDRPC_USE_INPLACE_BUFFER
#define WINDRPC_USE_INPLACE_BUFFER 0
#endif

// --WINDRPC_STACK_AND_BUFFER_DEFINES

#ifndef WINDRPC_MANUFACTURER_NAME
#define WINDRPC_MANUFACTURER_NAME "unknown"
#endif

#ifndef WINDRPC_MODEL_NUMBER
#define WINDRPC_MODEL_NUMBER "unknown"
#endif

#ifndef WINDRPC_HW_REVISION
#define WINDRPC_HW_REVISION "unknown"
#endif

#ifndef WINDRPC_FW_REVISION
#define WINDRPC_FW_REVISION "unknown"
#endif

#endif
