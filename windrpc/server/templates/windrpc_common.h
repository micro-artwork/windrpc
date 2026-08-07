#ifndef WINDRPC_COMMON_H
#define WINDRPC_COMMON_H

#include "windrpc_config.h"
#include <stdbool.h>
#include <pb.h>
#include <pb_encode.h>
#include <pb_decode.h>

// --WINDRPC_PB_HEADERS

#ifndef WINDRPC_PACKAGE_NAME
// --WINDRPC_PACKAGE_NAME
#endif


#ifndef WINDRPC_STATUS_MESSAGE_MAX_LEN
#define WINDRPC_STATUS_MESSAGE_MAX_LEN 64
#endif

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

#ifndef WINDRPC_CORE_VERSION_CODE
#define WINDRPC_CORE_VERSION_CODE 100
#endif

#ifndef WINDRPC_CORE_VERSION_NAME
#define WINDRPC_CORE_VERSION_NAME "0.1.0"
#endif

#define WINDRPC_STATUS_CODE(name) \
    WINDRPC_CAT3(WINDRPC_PACKAGE_NAME, _windrpc_types_StatusCode_STATUS_CODE_, name)

#define WINDRPC_COMMON_DEVICE_INFO_TYPE \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_common_DeviceInfo)

#define WINDRPC_COMMON_DEVICE_INFO_FIELDS \
    WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_common_DeviceInfo_fields)

#define WINDRPC_SERVICE_MSG_FIELDS(service_name, message_name) \
    WINDRPC_CAT6(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _, message_name, _fields)

#define WINDRPC_TYPES_MSG_FIELDS(message_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name, _fields)

#define WINDRPC_TYPES_TYPE(message_name) \
    WINDRPC_CAT3(WINDRPC_PACKAGE_NAME, _windrpc_types_, message_name)

#define WINDRPC_SERVICE_REQUEST_TYPE(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Request)

#define WINDRPC_SERVICE_RESPONSE_TYPE(service_name) \
    WINDRPC_CAT4(WINDRPC_PACKAGE_NAME, _windrpc_service_, service_name, _Response)

struct windrpc_handler_entry {
    uint16_t rpc_id;
    int32_t (*execute)(const void *req, void *res, void *context);
    bool has_response;
    const pb_msgdesc_t *req_fields;
    const pb_msgdesc_t *res_fields;
};

// --WINDRPC_RPC_INDEX_ENUM

#endif

