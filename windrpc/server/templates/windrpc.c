#include "windrpc.h"

#include <stdio.h>
#include <string.h>

LOG_MODULE_REGISTER(windrpc, WINDRPC_LOG_LEVEL);

static struct windrpc_device_info* device_info = NULL;

int32_t windrpc_init(struct windrpc_device_info* info) {
    device_info = info;
    LOG_INF("windrpc framework initialized.");
    return 0;
}

int32_t windrpc_on_ping(const void* req, rpc_common_PingResponse_t* res, void* context) {
    ARG_UNUSED(req);
    LOG_DBG("Execute: ping");
    if (res == NULL) return -1;
    memset(res, 0, sizeof(*res));
    res->core_version_code = WINDRPC_CORE_VERSION_CODE;
    strncpy(res->core_version_name, WINDRPC_CORE_VERSION_NAME, sizeof(res->core_version_name) - 1);
    res->spec_version_code = WINDRPC_SPEC_VERSION_CODE;
    strncpy(res->spec_version_name, WINDRPC_SPEC_VERSION_NAME, sizeof(res->spec_version_name) - 1);
    return 0;
}

int32_t windrpc_on_get_device_info(const void* req, rpc_common_DeviceInfo_t* res, void* context) {
    ARG_UNUSED(req);
    LOG_DBG("Execute: get_device_info");
    if (res == NULL) return -1;
    memset(res, 0, sizeof(*res));
    strncpy(res->manufacturer_name, WINDRPC_MANUFACTURER_NAME, sizeof(res->manufacturer_name) - 1);
    strncpy(res->model_number, WINDRPC_MODEL_NUMBER, sizeof(res->model_number) - 1);
    strncpy(res->hw_revision, WINDRPC_HW_REVISION, sizeof(res->hw_revision) - 1);
    strncpy(res->fw_revision, WINDRPC_FW_REVISION, sizeof(res->fw_revision) - 1);

    const char* serial = (device_info && device_info->serial_number)
                             ? device_info->serial_number
                             : "unknown";
    strncpy(res->serial_number, serial, sizeof(res->serial_number) - 1);
    return 0;
}

const char* windrpc_strerror(int32_t code) {
    switch (code) {
        case 0:  return "OK";
        case 1:  return "Cancelled";
        case 2:  return "Unknown error";
        case 3:  return "Invalid argument";
        case 4:  return "Deadline exceeded";
        case 5:  return "Resource not found";
        case 6:  return "Resource already exists";
        case 7:  return "Permission denied";
        case 8:  return "Resource exhausted";
        case 9:  return "Failed precondition";
        case 10: return "Operation aborted";
        case 11: return "Out of range";
        case 12: return "Unimplemented";
        case 13: return "Internal error";
        case 14: return "Service unavailable";
        case 15: return "Data loss";
        case 16: return "Unauthenticated";
        case 17: return "Invalid data format";
        case 18: return "Missing required field";
        case 19: return "Version mismatch";
        default: return "Unknown status code";
    }
}

void windrpc_set_error(struct windrpc_context* ctx, int32_t code, const char* message) {
    if (ctx == NULL) return;
    ctx->status_code = code;
    if (message != NULL && message[0] != '\0') {
        strncpy(ctx->status_message, message, sizeof(ctx->status_message) - 1);
        ctx->status_message[sizeof(ctx->status_message) - 1] = '\0';
    } else {
        ctx->status_message[0] = '\0';
    }
}

// --WINDRPC_FLAT_DISPATCH_TABLE

// Reserved System Error RPC ID (0x0000)
static int32_t send_flat_error_response(struct windrpc_buffer* buffer, uint16_t seq_id, int32_t code, const char* message) {
    uint8_t* tx_data = buffer->tx_data;
    if (!tx_data || buffer->tx_size < 6) {
        buffer->bytes_written = 0;
        return -1;
    }

    tx_data[0] = 0x00;
    tx_data[1] = 0x00;
    tx_data[2] = (uint8_t)(seq_id & 0xFF);
    tx_data[3] = (uint8_t)((seq_id >> 8) & 0xFF);

    WINDRPC_TYPES_TYPE(Status) status_msg = {0};
    status_msg.code = code;
    if (message && message[0] != '\0') {
        status_msg.has_message = true;
        strncpy((char*)status_msg.message, message, sizeof(status_msg.message) - 1);
        status_msg.message[sizeof(status_msg.message) - 1] = '\0';
    }

    pb_ostream_t ostream = pb_ostream_from_buffer(&tx_data[6], buffer->tx_size - 6);

    pb_encode_tag(&ostream, PB_WT_VARINT, 1);
    pb_encode_svarint(&ostream, status_msg.code);

    if (status_msg.has_message) {
        pb_encode_tag(&ostream, PB_WT_STRING, 2);
        pb_encode_string(&ostream, (const uint8_t*)status_msg.message, strlen(status_msg.message));
    }

    tx_data[4] = (uint8_t)(ostream.bytes_written & 0xFF);
    tx_data[5] = (uint8_t)((ostream.bytes_written >> 8) & 0xFF);
    buffer->bytes_written = 6 + (uint16_t)ostream.bytes_written;
    LOG_WRN("Encoded Flat System Error Response (Code: %d, Msg: '%s'). Total Size: %u bytes", code, message ? message : "", buffer->bytes_written);
    return 0;
}

// RX packet handler & O(1) direct lookup dispatcher
int32_t windrpc_handle(struct windrpc_transaction* txn) {
    struct windrpc_buffer* buffer = &txn->buffer;
    struct windrpc_context* ctx = &txn->context;

    LOG_DBG("Processing Flat RPC packet. Size: %u bytes", buffer->bytes_written);

    memset(ctx, 0, sizeof(struct windrpc_context));

    if (buffer->bytes_written < 6) {
        LOG_ERR("Packet size too small (%u bytes)", buffer->bytes_written);
        ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(INVALID_DATA_FORMAT);
        return -1;
    }

    // 6-byte header: [RPC_ID:2][SEQ_ID:2][PAYLOAD_LEN:2] (Little-Endian)
    uint8_t* rx_data = buffer->data;
    uint16_t rpc_id = (uint16_t)(rx_data[0] | ((uint16_t)rx_data[1] << 8));
    uint16_t seq_id = (uint16_t)(rx_data[2] | ((uint16_t)rx_data[3] << 8));
    uint16_t payload_len = (uint16_t)(rx_data[4] | ((uint16_t)rx_data[5] << 8));


    const struct windrpc_handler_entry* handler = windrpc_find_flat_handler(rpc_id);
    if (!handler) {
        LOG_ERR("Unknown RPC ID: 0x%04X", rpc_id);
        ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(UNIMPLEMENTED);
        snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "RPC ID 0x%04X not found", rpc_id);
        send_flat_error_response(buffer, seq_id, ctx->status_code, ctx->status_message);
        return -1;
    }

    ctx->handler = handler;

    pb_istream_t istream = pb_istream_from_buffer(&rx_data[6], payload_len);
    void* req_ptr = windrpc_get_flat_req_struct(rpc_id);

    if (handler->req_fields && req_ptr) {
        if (!pb_decode(&istream, handler->req_fields, req_ptr)) {
            LOG_ERR("Failed to decode payload for RPC ID 0x%04X: %s", rpc_id, PB_GET_ERROR(&istream));
            ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(INVALID_DATA_FORMAT);
            snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "Invalid data format");
            send_flat_error_response(buffer, seq_id, ctx->status_code, ctx->status_message);
            return -1;
        }
    }

    // Execute business logic handler callback
    void* res_ptr = windrpc_get_flat_res_struct(rpc_id);
    int32_t status = handler->execute(req_ptr, res_ptr, ctx);
    if (status != 0) {
        LOG_WRN("Execution failed with application error: %d", status);
        ctx->status_code = status;
        const char* msg = (ctx->status_message[0] != '\0') ? ctx->status_message : windrpc_strerror(status);
        send_flat_error_response(buffer, seq_id, status, msg);
        return status;
    }

    // REQUEST_ONLY pattern: skip TX response
    if (!handler->has_response) {
        buffer->bytes_written = 0;
        LOG_DBG("REQUEST_ONLY RPC 0x%04X: no response sent", rpc_id);
        return 0;
    }

    // Build TX response packet
    uint8_t* tx_data = buffer->tx_data;
    if (!tx_data || buffer->tx_size < 6) {
        LOG_ERR("TX buffer size too small");
        buffer->bytes_written = 0;
        return -1;
    }

    tx_data[0] = (uint8_t)(rpc_id & 0xFF);
    tx_data[1] = (uint8_t)((rpc_id >> 8) & 0xFF);
    tx_data[2] = (uint8_t)(seq_id & 0xFF);
    tx_data[3] = (uint8_t)((seq_id >> 8) & 0xFF);

    pb_ostream_t ostream = pb_ostream_from_buffer(&tx_data[6], buffer->tx_size - 6);
    if (handler->res_fields && res_ptr) {
        if (!pb_encode(&ostream, handler->res_fields, res_ptr)) {
            LOG_ERR("Failed to encode response for RPC ID 0x%04X", rpc_id);
            send_flat_error_response(buffer, seq_id, WINDRPC_STATUS_CODE(INTERNAL), "Failed to encode response");
            return -1;
        }
    }

    tx_data[4] = (uint8_t)(ostream.bytes_written & 0xFF);
    tx_data[5] = (uint8_t)((ostream.bytes_written >> 8) & 0xFF);
    buffer->bytes_written = 6 + (uint16_t)ostream.bytes_written;
    LOG_DBG("Encoded Flat response. Total Size: %u bytes", buffer->bytes_written);

    return 0;
}

// Transport-agnostic raw packet processing entry point
int32_t windrpc_process_packet(const uint8_t* rx_packet, uint16_t rx_len,
                               uint8_t* out_resp_buf, uint16_t max_resp_len, uint16_t* out_resp_len) {
    if (!rx_packet || rx_len < 6) {
        if (out_resp_len) *out_resp_len = 0;
        return -1;
    }

    static uint8_t tx_raw_buf[WINDRPC_MAX_BUFFER_SIZE];

    struct windrpc_transaction txn;
    memset(&txn, 0, sizeof(txn));
    txn.buffer.data = (uint8_t*)rx_packet;
    txn.buffer.size = rx_len;
    txn.buffer.bytes_written = rx_len;
    txn.buffer.tx_data = tx_raw_buf;
    txn.buffer.tx_size = sizeof(tx_raw_buf);

    int32_t err = windrpc_handle(&txn);

    if (!err && txn.buffer.bytes_written > 0 && out_resp_buf && out_resp_len) {
        uint16_t copy_len = (txn.buffer.bytes_written < max_resp_len) ? txn.buffer.bytes_written : max_resp_len;
        memcpy(out_resp_buf, txn.buffer.tx_data, copy_len);
        *out_resp_len = copy_len;
    } else if (out_resp_len) {
        *out_resp_len = 0;
    }

    return err;
}


