#ifndef WINDRPC_H
#define WINDRPC_H

#include "windrpc_common.h"

struct windrpc_device_info {
    char* serial_number;
};

// Packet RX/TX buffer descriptor
struct windrpc_buffer {
    uint8_t* data;
    uint16_t size;
    uint16_t bytes_written;

    uint8_t* tx_data;
    uint16_t tx_size;
};

// RPC execution context
struct windrpc_context {
    int32_t status_code;
    char status_message[WINDRPC_STATUS_MESSAGE_MAX_LEN];

    uint32_t which_payload;
    uint32_t service_tag;
    windrpc_rpc_idx_t rpc_idx;
    const struct windrpc_handler_entry* handler;
};

// Complete RPC transaction
struct windrpc_transaction {
    struct windrpc_buffer buffer;
    struct windrpc_context context;
};

int32_t windrpc_init(struct windrpc_device_info* device_info);

/**
 * @brief Dispatch incoming RPC packet and generate response frame into txn->buffer.tx_data.
 * 
 * @param txn Pointer to the RPC transaction structure.
 * @return 0  If frame processing completed and a response packet (either normal success response 
 *            or 0x0000 System Error packet) was written to txn->buffer.tx_data ready for transmission 
 *            (or 0 bytes written for REQUEST_ONLY RPCs).
 *         -1 If a fatal internal error occurred (e.g. input buffer < 6 bytes, NULL tx_data) 
 *            where no response frame could be generated.
 * 
 * @note Application-level status code is stored in txn->context.status_code.
 */
int32_t windrpc_handle(struct windrpc_transaction* txn);

int32_t windrpc_notify(struct windrpc_transaction* txn);
const char* windrpc_strerror(int32_t code);
void windrpc_set_error(struct windrpc_context* ctx, int32_t code, const char* message);

/**
 * @brief Transport-agnostic helper to process raw packet bytes and copy response frame.
 * 
 * @return 0 on successful frame production, non-zero on fatal internal error.
 */
int32_t windrpc_process_packet(const uint8_t* rx_packet, uint16_t rx_len,
                               uint8_t* out_resp_buf, uint16_t max_resp_len, uint16_t* out_resp_len);

// --WINDRPC_TYPEDEF_ALIASES

// --WINDRPC_NOTIFY_DECLARATIONS

#endif

