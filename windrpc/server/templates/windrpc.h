#ifndef WINDRPC_H
#define WINDRPC_H

#include "windrpc_common.h"
#include "windrpc_config.h"

#if WINDRPC_LOG_LEVEL > 0
#define LOG_ERR(...) LOG_PRINT("ERR", __VA_ARGS__)
#else
#define LOG_ERR(...)
#endif

#if WINDRPC_LOG_LEVEL > 1
#define LOG_WRN(...) LOG_PRINT("WRN", __VA_ARGS__)
#else
#define LOG_WRN(...)
#endif

#if WINDRPC_LOG_LEVEL > 2
#define LOG_INF(...) LOG_PRINT("INF", __VA_ARGS__)
#else
#define LOG_INF(...)
#endif

#if WINDRPC_LOG_LEVEL > 3
#define LOG_DBG(...) LOG_PRINT("DBG", __VA_ARGS__)
#else
#define LOG_DBG(...)
#endif

struct windrpc_buffer {
    uint8_t *data;
    uint16_t size;
    uint16_t bytes_written;
};

// union windrpc_operation {
struct windrpc_operation {
    windrpc_server_msg_t server_msg;
    windrpc_client_msg_t client_msg;
};

struct windrpc_procedure {
    bool (*decode_cmd)(pb_istream_t *stream, const pb_field_t *field, void **arg);
    int32_t (*execute)(struct windrpc_operation *operation, void *context);
    void (*encode_res)(windrpc_response_msg_t *message, void *context);
};

struct windrpc_context {
    // if message has repeated, string or bytes filed types,
    // need temporary variables to decode protobuf completely
    // union windrpc_user_arg arg;

    // request id
    uint8_t request_id[WINDRPC_REQUEST_ID_MAX_LEN];
    uint8_t request_id_len;

    // error status
    int32_t status_code;
    char status_message[WINDRPC_STATUS_MESSAGE_MAX_LEN];

    uint32_t which_payload;
    struct windrpc_procedure *proc;
};

struct windrpc_transaction {
    struct windrpc_buffer buffer;
    struct windrpc_context context;
    // union windrpc_operation operation;
    struct windrpc_operation operation;
};

typedef bool (*windrpc_decode_cmd_t)(pb_istream_t *stream, const pb_field_t *field, void **arg);
// typedef int32_t (*windrpc_execute_t)(windrpc_client_msg_t *message, struct windrpc_context *context);
typedef int32_t (*windrpc_execute_t)(struct windrpc_operation *operation, struct windrpc_context *context);
typedef void (*windrpc_encode_res_t)(windrpc_response_msg_t *message, struct windrpc_context *context);
typedef void (*windrpc_notify_t)(windrpc_response_msg_t *message, struct windrpc_context *context);

// --WINDRPC_STRUCTURES_FOR_SERVICE

int32_t windrpc_init(struct windrpc_user_service *services);
int32_t windrpc_handle(struct windrpc_transaction *txn);
int32_t windrpc_notify(struct windrpc_transaction *txn);

#endif  // WINDRPC_H
