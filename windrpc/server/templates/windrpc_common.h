#ifndef WINDRPC_COMMON_H
#define WINDRPC_COMMON_H

#include <pb_common.h>
#include <pb_decode.h>
#include <pb_encode.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// --WINDRPC_PB_HEADERS

#ifdef __ZEPHYR__

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>

#else

#define LOG_LEVEL_NONE 0
#define LOG_LEVEL_ERR 1
#define LOG_LEVEL_WRN 2
#define LOG_LEVEL_INF 3
#define LOG_LEVEL_DBG 4

#define LOG_MODULE_REGISTER(name, ...) \
    const static char *log_module_name = #name

#define LOG_PRINT(level, fmt, ...) printf("[%s] %s: " fmt "\n", level, log_module_name, ##__VA_ARGS__)

#endif  // #ifdef __ZEPHYR__

#define _CAT_IMPL(a, b) a##b
#define _CAT(a, b) _CAT_IMPL(a, b)
#define _GET_NTH_ARG(_1, _2, _3, _4, _5, _6, _7, _8, N, ...) N
#define _COUNT_VARARGS(...) _GET_NTH_ARG(__VA_ARGS__, 8, 7, 6, 5, 4, 3, 2, 1)
#define _VA_CAT_DISPATCHER(count) _CAT(_CAT, count)

#define WINDRPC_CAT(...) _VA_CAT_DISPATCHER(_COUNT_VARARGS(__VA_ARGS__))(__VA_ARGS__)

#define _CAT2(a, b) _CAT(a, b)
#define _CAT3(a, b, c) _CAT(_CAT2(a, b), c)
#define _CAT4(a, b, c, d) _CAT(_CAT3(a, b, c), d)
#define _CAT5(a, b, c, d, e) _CAT(_CAT4(a, b, c, d), e)
#define _CAT6(a, b, c, d, e, f) _CAT(_CAT5(a, b, c, d, e), f)
#define _CAT7(a, b, c, d, e, f, g) _CAT(_CAT6(a, b, c, d, e, f), g)
#define _CAT8(a, b, c, d, e, f, g, h) _CAT(_CAT7(a, b, c, d, e, f, g), h)

/* -------------------------------------------------------------------------- */
/*                                Package Name                                */
/* -------------------------------------------------------------------------- */

// --WINDRPC_PACKAGE_NAME

/* -------------------------------------------------------------------------- */
/*                                  Constants                                 */
/* -------------------------------------------------------------------------- */

#define WINDRPC_REQUEST_ID_TYPE_NONE 0
#define WINDRPC_REQUEST_ID_TYPE_STRING 1
#define WINDRPC_REQUEST_ID_TYPE_BYTES 2

#define WINDRPC_REQUEST_ID_MAX_LEN 37
#define WINDRPC_STATUS_MESSAGE_MAX_LEN 64

#define WINDRPC_STATUS_CODE(code) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_StatusCode_STATUS_CODE_, code)

#define WINDRPC_COMMAND_ID(SERVICE, COMMAND) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_RpcId_RPC_ID_, SERVICE, _, COMMAND)

#define WINDRPC_WITH_RESP WINDRPC_SERVER_RESPONSE_TAG
#define WINDRPC_WITHOUT_RESP 0

/* -------------------------------------------------------------------------- */
/*                               Message Fields                               */
/* -------------------------------------------------------------------------- */

#define WINDRPC_SERVER_MESSAGE_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_fields)

#define WINDRPC_CLIENT_MESSAGE_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_fields)

#define WINDRPC_TYPES_FIELDS(type_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_, type_name, _fields)

#define WINDRPC_REQUEST_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Request_fields)

#define WINDRPC_SERVICE_REQUEST_FIELDS(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request_fields)

#define WINDRPC_SERVICE_RESPONSE_FIELDS(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response_fields)

#define WINDRPC_TYPES_FILED(message_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name, _fields)

/* -------------------------------------------------------------------------- */
/*                           Message Initializations                          */
/* -------------------------------------------------------------------------- */

#define WINDRPC_SERVER_MESSAGE_INIT \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_init_zero)

#define WINDRPC_CLIENT_MESSAGE_INIT \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_init_zero)

/* -------------------------------------------------------------------------- */
/*                                Message Tags                                */
/* -------------------------------------------------------------------------- */

#define WINDRPC_VERSION_CODE \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_PlatformVersionCode_PLATFORM_VERSION_CODE)

#define WINDRPC_SERVER_RESPONSE_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_response_tag)

#define WINDRPC_SERVER_NOTIFICAION_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage_notification_tag)

#define WINDRPC_CLIENT_REQUEST_TAG \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage_request_tag)

#define WINDRPC_SERVICE_REQUEST_TAG(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Request_, service_name, _tag)

#define WINDRPC_SERVICE_RESPONSE_TAG(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Response_, service_name, _tag)

#define WINDRPC_SERVICE_NOTIFICATION_TAG(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Notification_, service_name, _tag)

#define WINDRPC_SERVICE_REQUEST_CMD_TAG(service_name, command_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request_, command_name, _tag)

#define WINDRPC_SERVICE_RESPONSE_RESULT_TAG(service_name, result_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response_, result_name, _tag)

#define WINDRPC_SERVICE_NOTIFICATION_EVENT_TAG(service_name, event_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Notification_, event_name, _tag)

/* -------------------------------------------------------------------------- */
/*                                Message Types                               */
/* -------------------------------------------------------------------------- */

typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ClientMessage) windrpc_client_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_ServerMessage) windrpc_server_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Request) windrpc_request_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Response) windrpc_response_msg_t;
typedef WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Notification) windrpc_notif_msg_t;

#define WINDRPC_TYPES_TYPE(message_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name)

#define WINDRPC_SERVICE_REQUEST_TYPE(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request)

#define WINDRPC_SERVICE_RESPONSE_TYPE(service_name) \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response)

/* -------------------------------------------------------------------------- */
/*                                Service Entry                               */
/* -------------------------------------------------------------------------- */

#define WINDRPC_DECODE_FUNC(decode_func_name, ...)                                                         \
    static bool decode_func_name(pb_istream_t *stream, const pb_field_t *field, void **arg) {              \
        struct windrpc_context *ctx = (struct windrpc_context *)*arg;                                      \
        switch (field->tag) {                                                                              \
            __VA_ARGS__                                                                                    \
            default:                                                                                       \
                ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(NOT_FOUND);                                \
                snprintf(ctx->status_message, sizeof(ctx->status_message), "Unknown Tag: %d", field->tag); \
                LOG_ERR("Unknown Tag: %d", field->tag);                                                    \
                return false;                                                                              \
        }                                                                                                  \
    }

#define WINDRPC_DECODE_SERVICE_ENTRY(service)                                                               \
    case WINDRPC_SERVICE_REQUEST_TAG(service): {                                                            \
        LOG_DBG("Decoding '" #service "' service request");                                                 \
        WINDRPC_SERVICE_REQUEST_TYPE(service) *msg = (WINDRPC_SERVICE_REQUEST_TYPE(service) *)field->pData; \
        msg->cb_command.funcs.decode = decode_service_##service;                                            \
        msg->cb_command.arg = ctx;                                                                          \
        return pb_decode(stream, WINDRPC_SERVICE_REQUEST_FIELDS(service), msg);                             \
    }

#define WINDRPC_DECODE_COMMAND_ENTRY(service, command, resp)  \
    case WINDRPC_SERVICE_REQUEST_CMD_TAG(service, command): { \
        ctx->proc = &windrpc_service.service->command;        \
        ctx->which_payload = resp;                            \
        if (ctx->proc->decode_cmd != NULL) {                  \
            return ctx->proc->decode_cmd(stream, field, arg); \
        }                                                     \
        return true;                                          \
    }

#define WINDRPC_DECODE_USER_COMMAND_ENTRY(service, command, resp) \
    case WINDRPC_SERVICE_REQUEST_CMD_TAG(service, command):       \
        LOG_DBG("Matched led rpc: display_pixels");               \
        ctx->proc = &windrpc_service.user->service->command;      \
        ctx->which_payload = resp;                                \
        if (ctx->proc->decode_cmd != NULL) {                      \
            return ctx->proc->decode_cmd(stream, field, arg);     \
        }                                                         \
        return true;

// --WINDRPC_DECODE_SERVICE_FUNC

// --WINDRPC_DECODE_COMMAND_FUNC_LIST

#endif  // WINDRPC_COMMON_H
