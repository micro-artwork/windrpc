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

/* -------------------------------------------------------------------------- */
/*                     Device Information (BLE DIS reference)                  */
/* -------------------------------------------------------------------------- */
// Override these macros at build time (e.g. -DWINDRPC_MANUFACTURER_NAME='"MyCompany"')
// or edit them directly in this file.

#ifndef WINDRPC_MANUFACTURER_NAME
#define WINDRPC_MANUFACTURER_NAME  "unknown"
#endif

#ifndef WINDRPC_MODEL_NUMBER
#define WINDRPC_MODEL_NUMBER       "unknown"
#endif

#ifndef WINDRPC_HW_REVISION
#define WINDRPC_HW_REVISION        "unknown"
#endif

#ifndef WINDRPC_FW_REVISION
#define WINDRPC_FW_REVISION        "unknown"
#endif

#endif