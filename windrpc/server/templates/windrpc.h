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
    uint8_t *data; // rx or inplace data buffer
    uint16_t size; // rx or inplace data size
    uint16_t bytes_written;

#if defined(WINDRPC_USE_INPLACE_BUFFER) && (WINDRPC_USE_INPLACE_BUFFER == 1)
    #define tx_data data
    #define tx_size size
#else
    uint8_t *tx_data;  // separate tx data buffer
    uint16_t tx_size;  // separate tx data size
#endif
};

// union windrpc_operation {
struct windrpc_operation {
    windrpc_server_msg_t server_msg;
    windrpc_client_msg_t client_msg;
};

struct windrpc_context {
    // request id
    uint8_t request_id[WINDRPC_REQUEST_ID_MAX_LEN];
    uint8_t request_id_len;

    // error status
    int32_t status_code;
    char status_message[WINDRPC_STATUS_MESSAGE_MAX_LEN];

    uint32_t which_payload;
    const struct windrpc_handler_entry *handler;
};

struct windrpc_transaction {
    struct windrpc_buffer buffer;
    struct windrpc_context context;
    struct windrpc_operation operation;
};

typedef bool (*windrpc_decode_req_t)(pb_istream_t *stream, const pb_field_t *field, void **arg);
typedef int32_t (*windrpc_execute_t)(struct windrpc_operation *operation, struct windrpc_context *context);
typedef void (*windrpc_encode_res_t)(windrpc_response_msg_t *message, struct windrpc_context *context);
typedef void (*windrpc_notify_t)(windrpc_response_msg_t *message, struct windrpc_context *context);

int32_t windrpc_init(struct windrpc_device_info *device_info);
int32_t windrpc_handle(struct windrpc_transaction *txn);
int32_t windrpc_notify(struct windrpc_transaction *txn);

#endif  // WINDRPC_H
