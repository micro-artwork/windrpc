#include "windrpc.h"
#include <stdio.h>
#include <string.h>

LOG_MODULE_REGISTER(WINDRPC, WINDRPC_LOG_LEVEL);

static int32_t decode_request(pb_istream_t *stream, struct windrpc_transaction *txn);
static int32_t encode_response(pb_ostream_t *stream, struct windrpc_transaction *txn);

int32_t execute_ping(const rpc_types_Empty_t *req, uint32_t *res, void *context) {
    LOG_DBG("Execute: ping");
    if (res) *res = WINDRPC_VERSION_CODE;
    return 0;
}

static struct windrpc_device_info *device_info = NULL;

int32_t execute_get_device_info(const rpc_types_Empty_t *req, rpc_common_DeviceInfo_t *res, void *context) {
    LOG_DBG("Execute: get_device_info");
    if (res == NULL) return -1;
    memset(res, 0, sizeof(*res));
    strncpy(res->manufacturer_name, WINDRPC_MANUFACTURER_NAME, sizeof(res->manufacturer_name) - 1);
    strncpy(res->model_number, WINDRPC_MODEL_NUMBER, sizeof(res->model_number) - 1);
    strncpy(res->hw_revision, WINDRPC_HW_REVISION, sizeof(res->hw_revision) - 1);
    strncpy(res->fw_revision, WINDRPC_FW_REVISION, sizeof(res->fw_revision) - 1);

    const char *serial = (device_info && device_info->serial_number)
                         ? device_info->serial_number : "unknown";
    strncpy(res->serial_number, serial, sizeof(res->serial_number) - 1);
    return 0;
}

// --WINDRPC_DISPATCH_TABLE

// --WINDRPC_GET_COMMAND_TAG_AND_INDEX_FUNCS

int32_t windrpc_init(struct windrpc_device_info *info) {
    device_info = info;
    LOG_INF("windrpc framework initialized.");
    return 0;
}

int32_t windrpc_handle(struct windrpc_transaction *txn) {
    struct windrpc_buffer *buffer = &txn->buffer;
    struct windrpc_context *ctx = &txn->context;

    LOG_DBG("Handling new RPC request. Size: %u bytes", buffer->bytes_written);

    // context reset
    memset(ctx, 0, sizeof(struct windrpc_context));
    ctx->which_payload = WINDRPC_SERVER_RESPONSE_TAG;

    pb_istream_t istream = pb_istream_from_buffer(buffer->data, buffer->bytes_written);
    int32_t status = decode_request(&istream, txn);

    if (status == 0) {
        if (ctx->handler != NULL && ctx->handler->execute != NULL) {
            const void *req_ptr = windrpc_get_req_ptr(&txn->operation.client_msg.payload.request, ctx->rpc_idx);
            void *res_ptr = windrpc_get_res_ptr(&txn->operation.server_msg.payload.response, ctx->rpc_idx);

            if (ctx->handler->has_response) {
                windrpc_set_response_result_tag(&txn->operation.server_msg.payload.response, ctx->rpc_idx, ctx->handler->res_tag);
                status = ctx->handler->execute(req_ptr, res_ptr, ctx);
            } else {
                status = ctx->handler->execute(req_ptr, NULL, ctx);
            }

            if (status != 0) {
                LOG_WRN("Execution failed with application error: %d", status);
                ctx->status_code = status;
            }
        } else if (ctx->status_code == 0) {
            ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(UNIMPLEMENTED);
            snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "Method not implemented");
            LOG_ERR("No execute_func found");
        }
    }

    if (ctx->which_payload == WINDRPC_SERVER_RESPONSE_TAG) {
        pb_ostream_t ostream = pb_ostream_from_buffer(buffer->tx_data, buffer->tx_size);
        status = encode_response(&ostream, txn);
        if (status != 0) {
            LOG_ERR("Encoding failed with framework error: %d", status);
            buffer->bytes_written = 0;
            return -1;
        }
        buffer->bytes_written = ostream.bytes_written;
        LOG_DBG("Encoded response. Size: %u bytes", buffer->bytes_written);

    } else {
        buffer->bytes_written = 0;
        LOG_DBG("Request handled. No response message required.");
    }
    return 0;
}

int32_t windrpc_notify(struct windrpc_transaction *txn) {
    struct windrpc_buffer *buffer = &txn->buffer;
    windrpc_server_msg_t *msg = &txn->operation.server_msg;
    msg->which_payload = WINDRPC_SERVER_NOTIFICAION_TAG;
    pb_ostream_t ostream = pb_ostream_from_buffer(buffer->tx_data, buffer->tx_size);
    if (!pb_encode(&ostream, WINDRPC_SERVER_MESSAGE_FIELDS, msg)) {
        LOG_ERR("Failed to encode notification stream: %s", PB_GET_ERROR(&ostream));
        return -1;
    }
    return 0;
}

/* -------------------------------------------------------------------------- */
/*                           Decode Request(Command)                          */
/* -------------------------------------------------------------------------- */

static int32_t decode_request(pb_istream_t *stream, struct windrpc_transaction *txn) {
    windrpc_client_msg_t *msg = &txn->operation.client_msg;
    struct windrpc_context *ctx = &txn->context;

    *msg = (windrpc_client_msg_t)WINDRPC_CLIENT_MESSAGE_INIT;

    if (!pb_decode(stream, WINDRPC_CLIENT_MESSAGE_FIELDS, msg)) {
        LOG_ERR("Failed to decode request stream: %s", PB_GET_ERROR(stream));
        ctx->status_code = WINDRPC_STATUS_CODE(INVALID_DATA_FORMAT);
        if (strlen(PB_GET_ERROR(stream)) == 0) {
            snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "%s", "Invalid data format");
        } else {
            snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "%s", PB_GET_ERROR(stream));
        }
        return -1;
    }

    windrpc_request_msg_t *req = &msg->payload.request;
    ctx->request_id_len = (uint8_t)req->request_id.size;
    if (ctx->request_id_len > 0) {
        if (ctx->request_id_len >= WINDRPC_REQUEST_ID_MAX_LEN) {
            ctx->request_id_len = WINDRPC_REQUEST_ID_MAX_LEN - 1;
        }
        memcpy(ctx->request_id, req->request_id.bytes, ctx->request_id_len);
        ctx->request_id[ctx->request_id_len] = '\0';
    }

    uint32_t service_tag = req->which_service;
    uint32_t command_tag = get_command_tag(req);
    windrpc_rpc_idx_t idx = windrpc_get_rpc_index(service_tag, command_tag);

    if (idx == WINDRPC_RPC_IDX_UNKNOWN) {
        ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(UNIMPLEMENTED);
        snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "Method not implemented");
        LOG_ERR("No RPC handler found for service tag: %u, command tag: %u", service_tag, command_tag);
        return 0;
    }

    ctx->rpc_idx = idx;
    ctx->service_tag = service_tag;
    ctx->handler = &rpc_dispatch_table[idx];
    ctx->which_payload = ctx->handler->has_response ? WINDRPC_SERVER_RESPONSE_TAG : 0;

    return 0;
}

/* -------------------------------------------------------------------------- */
/*                           Encode Response(Result)                          */
/* -------------------------------------------------------------------------- */

static int32_t encode_response(pb_ostream_t *stream, struct windrpc_transaction *txn) {
    struct windrpc_context *ctx = &txn->context;
    windrpc_server_msg_t *msg = &txn->operation.server_msg;

    msg->which_payload = WINDRPC_SERVER_RESPONSE_TAG;
    windrpc_response_msg_t *resp = &msg->payload.response;

    if (ctx->request_id_len > 0) {
        resp->request_id.size = ctx->request_id_len;
        memcpy(resp->request_id.bytes, ctx->request_id, ctx->request_id_len);
    }

    if (ctx->status_code != 0) {
        LOG_WRN("Encoding error response. Code: %d", ctx->status_code);
        resp->which_service = WINDRPC_SERVICE_RESPONSE_TAG(status);
        resp->service.status.code = ctx->status_code;
        if (ctx->status_message[0] != '\0') {
            strncpy((char *)resp->service.status.message, ctx->status_message, sizeof(resp->service.status.message) - 1);
        }
    } else if (ctx->handler != NULL && ctx->handler->has_response) {
        resp->which_service = ctx->service_tag;
    } else {
        LOG_ERR("Missing encode_res function for a method that requires a response.");
        return -1;
    }

    if (!pb_encode(stream, WINDRPC_SERVER_MESSAGE_FIELDS, msg)) {
        LOG_ERR("Failed to encode response stream: %s", PB_GET_ERROR(stream));
        return -1;
    }

    return 0;
}
