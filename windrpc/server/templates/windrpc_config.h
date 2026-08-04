/*
 * Copyright (c) 2026 WindRPC
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef WINDRPC_CONFIG_H
#define WINDRPC_CONFIG_H

#include "windrpc_common.h"

/* -------------------------------------------------------------------------- */
/*                              Envelope Mode                                 */
/* -------------------------------------------------------------------------- */
#define WINDRPC_ENVELOPE_NESTED 0
#define WINDRPC_ENVELOPE_FLAT 1

#ifndef WINDRPC_ENVELOPE_MODE
#define WINDRPC_ENVELOPE_MODE WINDRPC_ENVELOPE_NESTED
#endif

#define WINDRPC_LOG_LEVEL LOG_LEVEL_INF

// [Default] 0: Separate rx/tx buffers (Double Buffer) for safety.
//           1: Share a single buffer for rx/tx (In-place) to save RAM.
#ifndef WINDRPC_USE_INPLACE_BUFFER
#define WINDRPC_USE_INPLACE_BUFFER 0
#endif

/* -------------------------------------------------------------------------- */
/*                      Stack & Buffer Sizes (Auto-Generated)                 */
/* -------------------------------------------------------------------------- */
// --WINDRPC_STACK_AND_BUFFER_DEFINES

/* -------------------------------------------------------------------------- */
/*                     Device Information (BLE DIS reference)                  */
/* -------------------------------------------------------------------------- */
// Override these macros at build time (e.g. -DWINDRPC_MANUFACTURER_NAME='"MyCompany"')
// or edit them directly in this file.

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
