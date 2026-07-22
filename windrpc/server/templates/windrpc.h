#ifndef WINDRPC_H
#define WINDRPC_H

#include "windrpc_common.h"

// --WINDRPC_TYPEDEF_ALIASES

struct windrpc_device_info {
    char *serial_number;
};

struct windrpc_buffer {
    uint8_t *data;
    uint16_t size;
    uint16_t bytes_written;

    uint8_t *tx_data;  // separate tx data buffer
    uint16_t tx_size;  // separate tx data size
};

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
    uint32_t service_tag;
    windrpc_rpc_idx_t rpc_idx;
    const struct windrpc_handler_entry *handler;
};

struct windrpc_transaction {
    struct windrpc_buffer buffer;
    struct windrpc_context context;
    struct windrpc_operation operation;
};

int32_t windrpc_init(struct windrpc_device_info *device_info);
int32_t windrpc_handle(struct windrpc_transaction *txn);
int32_t windrpc_notify(struct windrpc_transaction *txn);

#endif  // WINDRPC_H
