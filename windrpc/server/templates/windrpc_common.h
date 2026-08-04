/*
 * Copyright (c) 2026 WindRPC
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef WINDRPC_COMMON_H
#define WINDRPC_COMMON_H

#include "windrpc_config.h"
#include <pb.h>
#include <pb_encode.h>
#include <pb_decode.h>

// --WINDRPC_PB_HEADERS

#ifndef WINDRPC_PACKAGE_NAME
// --WINDRPC_PACKAGE_NAME
#endif

#ifndef WINDRPC_REQUEST_ID_MAX_LEN
#define WINDRPC_REQUEST_ID_MAX_LEN 38
#endif

#ifndef WINDRPC_STATUS_MESSAGE_MAX_LEN
#define WINDRPC_STATUS_MESSAGE_MAX_LEN 64
#endif

/* -------------------------------------------------------------------------- */
/*                              Logging Fallbacks                             */
/* -------------------------------------------------------------------------- */

#ifdef __ZEPHYR__
#include <zephyr/logging/log.h>
#else
#ifndef LOG_MODULE_REGISTER
#define LOG_MODULE_REGISTER(name, level)
#endif

#ifndef LOG_DBG
#define LOG_DBG(...)
#endif

#ifndef LOG_INF
#define LOG_INF(...)
#endif

#ifndef LOG_WRN
#define LOG_WRN(...)
#endif

#ifndef LOG_ERR
#define LOG_ERR(...)
#endif

#ifndef ARG_UNUSED
#define ARG_UNUSED(x) (void)(x)
#endif
#endif

/* -------------------------------------------------------------------------- */
/*                              Helper Macros                                 */
/* -------------------------------------------------------------------------- */

#define WINDRPC_CAT_IMPL(a, b) a##b
#define WINDRPC_CAT(a, b) WINDRPC_CAT_IMPL(a, b)

#define WINDRPC_CAT3_IMPL(a, b, c) a##b##c
#define WINDRPC_CAT3(a, b, c) WINDRPC_CAT3_IMPL(a, b, c)

#define WINDRPC_CAT4_IMPL(a, b, c, d) a##b##c##d
#define WINDRPC_CAT4(a, b, c, d) WINDRPC_CAT4_IMPL(a, b, c, d)

#define WINDRPC_CAT5_IMPL(a, b, c, d, e) a##b##c##d##e
#define WINDRPC_CAT5(a, b, c, d, e) WINDRPC_CAT5_IMPL(a, b, c, d, e)

#define WINDRPC_CAT6_IMPL(a, b, c, d, e, f) a##b##c##d##e##f
#define WINDRPC_CAT6(a, b, c, d, e, f) WINDRPC_CAT6_IMPL(a, b, c, d, e, f)

#define WINDRPC_STATUS_CODE(name) \
    WINDRPC_CAT3(WINDRPC_PACKAGE_NAME, _windrpc_types_StatusCode_STATUS_CODE_, name)

#define WINDRPC_VERSION_CODE \
    WINDRPC_CAT3(WINDRPC_PACKAGE_NAME, _windrpc_types_PlatformVersionCode_, PLATFORM_VERSION_CODE)

#define WINDRPC_COMMON_DEVICE_INFO_TYPE \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_common_DeviceInfo)

#define WINDRPC_COMMON_DEVICE_INFO_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_common_DeviceInfo_fields)

#define WINDRPC_SERVICE_MSG_FIELDS(service_name, message_name) \
    WINDRPC_CAT6(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _, message_name, _fields)

#define WINDRPC_TYPES_MSG_FIELDS(message_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name, _fields)

#if WINDRPC_ENVELOPE_MODE != WINDRPC_ENVELOPE_FLAT

#define WINDRPC_CLIENT_MESSAGE_INIT \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_init_default)

#define WINDRPC_CLIENT_MESSAGE_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_fields)

#define WINDRPC_SERVER_MESSAGE_INIT \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_init_default)

#define WINDRPC_SERVER_MESSAGE_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_fields)

#define WINDRPC_REQUEST_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Request_fields)

#define WINDRPC_RESPONSE_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Response_fields)

/* -------------------------------------------------------------------------- */
/*                                Service Tags                                */
/* -------------------------------------------------------------------------- */

#define WINDRPC_SERVER_NOTIFICAION_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_notification_tag)

#define WINDRPC_CLIENT_REQUEST_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_request_tag)

#define WINDRPC_SERVER_RESPONSE_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_response_tag)

#define WINDRPC_SERVICE_REQUEST_TAG(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_core_Request_, service_name, _tag)

#define WINDRPC_SERVICE_RESPONSE_TAG(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_core_Response_, service_name, _tag)

#define WINDRPC_SERVICE_NOTIFICATION_TAG(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_core_Notification_, service_name, _tag)

#define WINDRPC_SERVICE_REQUEST_CMD_TAG(service_name, command_name) \
    WINDRPC_CAT6(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request_, command_name, _tag)

#define WINDRPC_SERVICE_RESPONSE_RESULT_TAG(service_name, result_name) \
    WINDRPC_CAT6(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response_, result_name, _tag)

#define WINDRPC_SERVICE_NOTIFICATION_EVENT_TAG(service_name, event_name) \
    WINDRPC_CAT6(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Notification_, event_name, _tag)

/* -------------------------------------------------------------------------- */
/*                                Message Types                               */
/* -------------------------------------------------------------------------- */

typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage) windrpc_client_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage) windrpc_server_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Request) windrpc_request_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Response) windrpc_response_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Notification) windrpc_notif_msg_t;

#endif /* WINDRPC_ENVELOPE_MODE != WINDRPC_ENVELOPE_FLAT */

#define WINDRPC_TYPES_TYPE(message_name) \
    WINDRPC_CAT3(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name)

#define WINDRPC_SERVICE_REQUEST_TYPE(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request)

#define WINDRPC_SERVICE_RESPONSE_TYPE(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response)

/* -------------------------------------------------------------------------- */
/*                               Dispatch Table                               */
/* -------------------------------------------------------------------------- */

#if WINDRPC_ENVELOPE_MODE == WINDRPC_ENVELOPE_FLAT
struct windrpc_handler_entry {
    uint16_t rpc_id;
    int32_t (*execute)(const void *req, void *res, void *context);
    bool has_response;
    const pb_msgdesc_t *req_fields;
    const pb_msgdesc_t *res_fields;
};
#else
struct windrpc_handler_entry {
    int32_t (*execute)(const void *req, void *res, void *context);
    bool has_response;
    uint32_t res_tag;
};
#endif

// --WINDRPC_RPC_INDEX_ENUM

#endif  // WINDRPC_COMMON_H

