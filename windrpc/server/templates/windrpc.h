#ifndef WINDRPC_H
#define WINDRPC_H

#include "windrpc_common.h"

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

#if WINDRPC_ENVELOPE_MODE != WINDRPC_ENVELOPE_FLAT
struct windrpc_operation {
    windrpc_server_msg_t server_msg;
    windrpc_client_msg_t client_msg;
};
#endif

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
#if WINDRPC_ENVELOPE_MODE != WINDRPC_ENVELOPE_FLAT
    struct windrpc_operation operation;
#endif
};

int32_t windrpc_init(struct windrpc_device_info *device_info);
int32_t windrpc_handle(struct windrpc_transaction *txn);
int32_t windrpc_notify(struct windrpc_transaction *txn);
const char *windrpc_strerror(int32_t code);
void windrpc_set_error(struct windrpc_context *ctx, int32_t code, const char *message);

int32_t windrpc_process_packet(const uint8_t *rx_packet, uint16_t rx_len, uint32_t transport_id,
			      uint8_t *out_resp_buf, uint16_t max_resp_len, uint16_t *out_resp_len);

/* -------------------------------------------------------------------------- */
/*                      WindRPC Type Aliases (Shortcuts)                      */
/* -------------------------------------------------------------------------- */
// --WINDRPC_TYPEDEF_ALIASES

/* -------------------------------------------------------------------------- */
/*                      Notification Function Declarations                    */
/* -------------------------------------------------------------------------- */
// --WINDRPC_NOTIFY_DECLARATIONS

#endif  // WINDRPC_H
