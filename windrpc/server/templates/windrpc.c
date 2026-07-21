#include "windrpc.h"

LOG_MODULE_REGISTER(WINDRPC, WINDRPC_LOG_LEVEL);

static int32_t decode_request(pb_istream_t *stream, struct windrpc_transaction *txn);
static int32_t encode_response(pb_ostream_t *stream, struct windrpc_transaction *txn);

int32_t execute_ping(struct windrpc_operation *operation, void *context) {
    LOG_DBG("Execute: ping");
    return 0;
}

void encode_ping(windrpc_response_msg_t *message, void *context) {
    message->which_service = WINDRPC_SERVICE_RESPONSE_TAG(common);
    message->service.common.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, ping);
    message->service.common.result.ping = WINDRPC_VERSION_CODE;
}

static struct windrpc_device_info *device_info = NULL;

int32_t execute_get_device_info(struct windrpc_operation *operation, void *context) {
    LOG_DBG("Execute: get_device_info");
    return 0;
}

static bool encode_device_info_result(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    WINDRPC_COMMON_DEVICE_INFO_TYPE *info =
        (WINDRPC_COMMON_DEVICE_INFO_TYPE *)field->pData;
    if (info == NULL) return false;

    memset(info, 0, sizeof(*info));
    strncpy(info->manufacturer_name, WINDRPC_MANUFACTURER_NAME, sizeof(info->manufacturer_name) - 1);
    strncpy(info->model_number, WINDRPC_MODEL_NUMBER, sizeof(info->model_number) - 1);
    strncpy(info->hw_revision, WINDRPC_HW_REVISION, sizeof(info->hw_revision) - 1);
    strncpy(info->fw_revision, WINDRPC_FW_REVISION, sizeof(info->fw_revision) - 1);

    const char *serial = (device_info && device_info->serial_number)
                         ? device_info->serial_number : "unknown";
    strncpy(info->serial_number, serial, sizeof(info->serial_number) - 1);

    return true;
}

void encode_get_device_info(windrpc_response_msg_t *message, void *context) {
    message->which_service = WINDRPC_SERVICE_RESPONSE_TAG(common);
    message->service.common.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, get_device_info);
    message->service.common.cb_result.funcs.encode = encode_device_info_result;
    message->service.common.cb_result.arg = NULL;
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
            status = ctx->handler->execute(&txn->operation, ctx);
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

static bool decode_request_id(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;
    size_t len = stream->bytes_left;
    if (len >= WINDRPC_REQUEST_ID_MAX_LEN) return false;
    if (!pb_read(stream, ctx->request_id, len)) return false;
    ctx->request_id_len = len;
    ctx->request_id[len] = '\0';
    return true;
}

static bool decode_payload(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;

    if (field->tag == WINDRPC_CLIENT_REQUEST_TAG) {
        LOG_DBG("Decoding 'request' submessage.");

        windrpc_request_msg_t *req = (windrpc_request_msg_t *)field->pData;

        if (WINDRPC_REQUEST_ID_TYPE) {
            req->request_id.funcs.decode = decode_request_id;
            req->request_id.arg = ctx;
        }

        if (!pb_decode(stream, WINDRPC_REQUEST_FIELDS, req)) {
            LOG_ERR("Failed to decode Request sub-message: %s", PB_GET_ERROR(stream));
            return false;
        }

        return true;
    }

    LOG_ERR("Unknown payload tag in ClientMessage: %d", (int)field->tag);
    return false;
}

static int32_t decode_request(pb_istream_t *stream, struct windrpc_transaction *txn) {
    windrpc_client_msg_t *msg = &txn->operation.client_msg;
    struct windrpc_context *ctx = &txn->context;

    *msg = (windrpc_client_msg_t)WINDRPC_CLIENT_MESSAGE_INIT;
    msg->cb_payload.funcs.decode = decode_payload;
    msg->cb_payload.arg = ctx;

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
    uint32_t service_tag = req->which_service;
    uint32_t command_tag = get_command_tag(req);
    windrpc_rpc_idx_t idx = windrpc_get_rpc_index(service_tag, command_tag);

    if (idx == WINDRPC_RPC_IDX_UNKNOWN) {
        ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(UNIMPLEMENTED);
        snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "Method not implemented");
        LOG_ERR("No RPC handler found for service tag: %u, command tag: %u", service_tag, command_tag);
        return 0;
    }

    ctx->handler = &rpc_dispatch_table[idx];
    ctx->which_payload = ctx->handler->has_response ? WINDRPC_SERVER_RESPONSE_TAG : 0;

    return 0;
}

/* -------------------------------------------------------------------------- */
/*                           Encode Response(Result)                          */
/* -------------------------------------------------------------------------- */

static bool encode_request_id(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;
    if (!pb_encode_tag_for_field(stream, field)) return false;
    return pb_encode_string(stream, (uint8_t *)ctx->request_id, ctx->request_id_len);
}

static bool encode_string(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    const char *str = (const char *)(*arg);
    if (str == NULL) {
        str = "";
    }
    printf("[windrpc_encode_string]: %s\n", str);
    if (!pb_encode_tag_for_field(stream, field)) return false;
    return pb_encode_string(stream, (const uint8_t *)str, strlen(str));
}

static int32_t encode_response(pb_ostream_t *stream, struct windrpc_transaction *txn) {
    struct windrpc_context *ctx = &txn->context;
    windrpc_server_msg_t *msg = &txn->operation.server_msg;

    *msg = (windrpc_server_msg_t)WINDRPC_SERVER_MESSAGE_INIT;
    msg->which_payload = WINDRPC_SERVER_RESPONSE_TAG;
    windrpc_response_msg_t *resp = &msg->payload.response;

    if (WINDRPC_REQUEST_ID_TYPE) {
        LOG_DBG("Encoding response for request_id: %s", ctx->request_id);
        resp->request_id.funcs.encode = encode_request_id;
        resp->request_id.arg = ctx;
    }

    if (ctx->status_code != 0) {
        LOG_WRN("Encoding error response. Code: %d", ctx->status_code);
        resp->which_service = WINDRPC_SERVICE_RESPONSE_TAG(status);
        resp->service.status.code = ctx->status_code;
        if (ctx->status_message[0] != '\0') {
            resp->service.status.message.funcs.encode = encode_string;
            resp->service.status.message.arg = ctx->status_message;
        }
    } else if (ctx->handler != NULL && ctx->handler->encode_res != NULL) {
        ctx->handler->encode_res(resp, ctx);
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
