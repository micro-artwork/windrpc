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

static struct windrpc_service_common windrpc_common_service = {
    .ping = {
        .decode_cmd = NULL,
        .encode_res = encode_ping,
        .execute = execute_ping,
    }};

struct windrpc_service windrpc_service = {
    .common = NULL,
    .user = NULL,
};

int32_t windrpc_init(struct windrpc_user_service *service) {
    windrpc_service.common = &windrpc_common_service;
    windrpc_service.user = service;

    if (windrpc_service.user == NULL) {
        LOG_ERR("windrpc_service_internal is NULL");
        return -1;
    }

    // --WINDRPC_SERVICE_NULL_CHECK
    if (windrpc_service.user->led == NULL || windrpc_service.user->power == NULL) {
        LOG_ERR("windrpc user service are NULL");
        return -1;
    }

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
        if (ctx->proc != NULL && ctx->proc->execute != NULL) {
            // .client_msg.payload.request
            status = ctx->proc->execute(&txn->operation, ctx);
            if (status != 0) {
                // 실행 오류는 클라이언트에게 응답해야 할 애플리케이션 레벨 오류
                LOG_WRN("Execution failed with application error: %d", status);
                ctx->status_code = status;
                // 필요하다면 status 코드에 맞는 오류 메시지를 execution 단계에서 ctx->error_message에 지정
            }
        } else {
            ctx->status_code = (int32_t)WINDRPC_STATUS_CODE(UNIMPLEMENTED);
            snprintf(ctx->status_message, WINDRPC_STATUS_MESSAGE_MAX_LEN, "Method not implemented");
            LOG_ERR("No execute_func found");
        }
    }

    if (ctx->which_payload == WINDRPC_SERVER_RESPONSE_TAG) {
        pb_ostream_t ostream = pb_ostream_from_buffer(buffer->data, buffer->size);
        status = encode_response(&ostream, txn);
        if (status != 0) {
            LOG_ERR("Encoding failed with framework error: %d", status);
            buffer->bytes_written = 0;  // 인코딩 실패 시 응답을 보낼 수 없음
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
    pb_ostream_t ostream = pb_ostream_from_buffer(buffer->data, buffer->size);
    if (!pb_encode(&ostream, WINDRPC_SERVER_MESSAGE_FIELDS, msg)) {
        LOG_ERR("Failed to encode notification stream: %s", PB_GET_ERROR(&ostream));
        return -1;
    }
    return 0;
}

/* -------------------------------------------------------------------------- */
/*                           Decode Request(Command)                          */
/* -------------------------------------------------------------------------- */

WINDRPC_DECODE_COMMAND_FUNC_LIST

WINDRPC_DECODE_SERVICE_FUNC

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

        req->cb_service.funcs.decode = decode_service;
        req->cb_service.arg = ctx;

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
    } else if (ctx->proc != NULL && ctx->proc->encode_res != NULL) {
        ctx->proc->encode_res(resp, ctx);
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
