#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "windrpc.h"

#define BUFFER_SIZE 512
static uint8_t shared_buffer[BUFFER_SIZE];
static uint8_t shared_tx_buffer[BUFFER_SIZE];

#define CORE_TYPE(t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_, t)
#define CORE_FIELDS(t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_, t, _fields)
#define CORE_INIT(t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_, t, _init_zero)
#define CORE_TAG(t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_, t, _tag)

#define SVC_TYPE(svc, t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, svc, _, t)
#define SVC_FIELDS(svc, t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, svc, _, t, _fields)
#define SVC_INIT(svc, t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, svc, _, t, _init_zero)
#define SVC_TAG(svc, t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_service_, svc, _, t, _tag)

#define TYPES_FIELDS(t) WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_types_, t, _fields)

// Mock 서비스 실행 상태 저장용 전역 변수
static struct {
    int display_pixels_called;
    uint32_t last_colors[10];
    int last_colors_count;

    int read_power_info_called;
} mock_state;

static bool decode_server_message_safely(struct windrpc_transaction *txn, windrpc_response_msg_t *out_resp);

static struct {
    CORE_TYPE(ServerMessage) server_msg;
    char request_id[38];
} decode_result;

/* -------------------------------------------------------------------------- */
/*                                LED 서비스 모의 구현                        */
/* -------------------------------------------------------------------------- */
static bool decode_display_pixels(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    SVC_TYPE(led, PixelData) msg = SVC_INIT(led, PixelData);

    if (!pb_decode(stream, SVC_FIELDS(led, PixelData), &msg)) {
        return false;
    }
    mock_state.last_colors_count = msg.colors_count;
    for (pb_size_t i = 0; i < msg.colors_count && i < 10; ++i) {
        mock_state.last_colors[i] = msg.colors[i];
    }
    return true;
}

int32_t execute_display_pixels(struct windrpc_operation *operation, void *context) {
    mock_state.display_pixels_called++;
    SVC_TYPE(led, PixelData) *pixels =
        &operation->client_msg.payload.request.service.led.command.display_pixels;
    mock_state.last_colors_count = pixels->colors_count;
    for (pb_size_t i = 0; i < pixels->colors_count && i < 10; ++i) {
        mock_state.last_colors[i] = pixels->colors[i];
    }
    return 0;
}

int32_t execute_read_power_info(struct windrpc_operation *operation, void *context) {
    mock_state.read_power_info_called++;
    return 0;
}

static bool encode_power_result(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    SVC_TYPE(power, PowerInfo) *info = (SVC_TYPE(power, PowerInfo) *)field->pData;
    info->voltage_mill = 12000;
    info->ampere_mill = 500;
    return true;
}

void encode_read_power_info(windrpc_response_msg_t *response, void *context) {
    response->which_service = WINDRPC_SERVICE_RESPONSE_TAG(power);
    response->service.power.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(power, read_power_info);
    response->service.power.cb_result.funcs.encode = encode_power_result;
    response->service.power.cb_result.arg = NULL;
}

int32_t execute_subscribe_power_notification(struct windrpc_operation *operation, void *context) {
    return 0;
}

void encode_subscribe_power_notification(windrpc_response_msg_t *response, void *context) {
    response->which_service = WINDRPC_SERVICE_RESPONSE_TAG(power);
    response->service.power.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(power, subscribe_power_notification);
}

/* -------------------------------------------------------------------------- */
/*                          인코딩/디코딩용 헬퍼 함수                         */
/* -------------------------------------------------------------------------- */
static bool encode_string_callback(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    const char *str = (const char *)*arg;
    if (!pb_encode_tag_for_field(stream, field)) return false;
    return pb_encode_string(stream, (const uint8_t *)str, strlen(str));
}

static bool decode_string_callback(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    size_t len = stream->bytes_left;
    printf("[decode_string_callback] bytes_left: %zu\n", len);
    
    if (arg == NULL || *arg == NULL) {
        pb_byte_t temp_buf[64];
        while (len > 0) {
            size_t read_len = (len > sizeof(temp_buf)) ? sizeof(temp_buf) : len;
            if (!pb_read(stream, temp_buf, read_len)) return false;
            len -= read_len;
        }
        return true;
    }
    
    char *dest = (char *)*arg;
    if (len >= 37) return false;
    if (!pb_read(stream, (pb_byte_t *)dest, len)) return false;
    dest[len] = '\0';
    printf("[decode_string_callback] decoded: '%s'\n", dest);
    return true;
}

/* -------------------------------------------------------------------------- */
/*                                유닛 테스트 케이스                          */
/* -------------------------------------------------------------------------- */

// 1. Ping 테스트 (Core built-in service)
static void test_ping(void) {
    printf("Running test_ping...\n");

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
#if !defined(WINDRPC_USE_INPLACE_BUFFER) || (WINDRPC_USE_INPLACE_BUFFER == 0)
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
#endif
            .bytes_written = 0
        },
        .context = {0},
        .operation = {0}
    };

    // ClientMessage 빌드
    CORE_TYPE(ClientMessage) msg = CORE_INIT(ClientMessage);
    msg.which_payload = WINDRPC_CLIENT_REQUEST_TAG;
    CORE_TYPE(Request) *req = &msg.payload.request;
    
    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "tx-ping-123";

    req->which_service = WINDRPC_SERVICE_REQUEST_TAG(common);
    req->service.common.which_command = WINDRPC_SERVICE_REQUEST_CMD_TAG(common, ping);

    // 인코딩
    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    bool ok = pb_encode(&ostream, WINDRPC_CLIENT_MESSAGE_FIELDS, &msg);
    assert(ok);
    txn.buffer.bytes_written = ostream.bytes_written;

    // RPC 핸들러 기동
    int32_t ret = windrpc_handle(&txn);
    assert(ret == 0);
    assert(txn.buffer.bytes_written > 0);

    // 응답 디코딩 및 검증
    ok = decode_server_message_safely(&txn, &decode_result.server_msg.payload.response);
    assert(ok);
    printf("[test_ping] rx_req_id: '%s'\n", decode_result.request_id);
    if (strcmp(decode_result.request_id, "tx-ping-123") != 0) {
        printf("ERROR: rx_req_id mismatch! Expected 'tx-ping-123', got '%s'\n", decode_result.request_id);
        exit(1);
    }
    
    windrpc_response_msg_t *resp = &decode_result.server_msg.payload.response;
    assert(resp->which_service == WINDRPC_SERVICE_RESPONSE_TAG(common));
    assert(resp->service.common.which_result == WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, ping));
    assert(resp->service.common.result.ping == WINDRPC_VERSION_CODE);

    printf("test_ping PASSED!\n");
}

// 2. LED display_pixels 테스트 (REQUEST_ONLY)
static void test_display_pixels(void) {
    printf("Running test_display_pixels...\n");
    memset(&mock_state, 0, sizeof(mock_state));

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
#if !defined(WINDRPC_USE_INPLACE_BUFFER) || (WINDRPC_USE_INPLACE_BUFFER == 0)
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
#endif
            .bytes_written = 0
        },
        .context = {0},
        .operation = {0}
    };

    uint32_t test_colors[10];
    for (int i = 0; i < 10; ++i) {
        test_colors[i] = 0xAA0000 + i;
    }

    CORE_TYPE(ClientMessage) msg = CORE_INIT(ClientMessage);
    msg.which_payload = WINDRPC_CLIENT_REQUEST_TAG;
    CORE_TYPE(Request) *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "tx-led-456";

    req->which_service = WINDRPC_SERVICE_REQUEST_TAG(led);
    req->service.led.which_command = WINDRPC_SERVICE_REQUEST_CMD_TAG(led, display_pixels);
    req->service.led.command.display_pixels.colors_count = 10;
    for (int i = 0; i < 10; ++i) {
        req->service.led.command.display_pixels.colors[i] = test_colors[i];
    }

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    bool ok = pb_encode(&ostream, WINDRPC_CLIENT_MESSAGE_FIELDS, &msg);
    assert(ok);
    txn.buffer.bytes_written = ostream.bytes_written;

    int32_t ret = windrpc_handle(&txn);
    assert(ret == 0);

    assert(txn.buffer.bytes_written == 0);

    assert(mock_state.display_pixels_called == 1);
    assert(mock_state.last_colors_count == 10);
    for (int i = 0; i < 10; ++i) {
        assert(mock_state.last_colors[i] == (0xAA0000 + i));
    }

    printf("test_display_pixels PASSED!\n");
}

// 3. Power read_power_info 테스트 (REQUEST_RESPONSE)
static void test_read_power_info(void) {
    printf("Running test_read_power_info...\n");
    memset(&mock_state, 0, sizeof(mock_state));

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
#if !defined(WINDRPC_USE_INPLACE_BUFFER) || (WINDRPC_USE_INPLACE_BUFFER == 0)
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
#endif
            .bytes_written = 0
        },
        .context = {0},
        .operation = {0}
    };

    CORE_TYPE(ClientMessage) msg = CORE_INIT(ClientMessage);
    msg.which_payload = WINDRPC_CLIENT_REQUEST_TAG;
    CORE_TYPE(Request) *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "tx-power-789";

    req->which_service = WINDRPC_SERVICE_REQUEST_TAG(power);
    req->service.power.which_command = WINDRPC_SERVICE_REQUEST_CMD_TAG(power, read_power_info);

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    bool ok = pb_encode(&ostream, WINDRPC_CLIENT_MESSAGE_FIELDS, &msg);
    assert(ok);
    txn.buffer.bytes_written = ostream.bytes_written;

    int32_t ret = windrpc_handle(&txn);
    assert(ret == 0);
    assert(txn.buffer.bytes_written > 0);

    ok = decode_server_message_safely(&txn, &decode_result.server_msg.payload.response);
    assert(ok);
    assert(strcmp(decode_result.request_id, "tx-power-789") == 0);

    windrpc_response_msg_t *resp = &decode_result.server_msg.payload.response;
    assert(resp->which_service == WINDRPC_SERVICE_RESPONSE_TAG(power));
    assert(resp->service.power.which_result == WINDRPC_SERVICE_RESPONSE_RESULT_TAG(power, read_power_info));
    
    assert(resp->service.power.result.read_power_info.voltage_mill == 12000);
    assert(resp->service.power.result.read_power_info.ampere_mill == 500);

    assert(mock_state.read_power_info_called == 1);

    printf("test_read_power_info PASSED!\n");
}

// 4. 지원하지 않는 요청에 대한 에러 핸들링 테스트
static void test_unimplemented_error(void) {
    printf("Running test_unimplemented_error...\n");

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
#if !defined(WINDRPC_USE_INPLACE_BUFFER) || (WINDRPC_USE_INPLACE_BUFFER == 0)
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
#endif
            .bytes_written = 0
        },
        .context = {0},
        .operation = {0}
    };

    CORE_TYPE(ClientMessage) msg = CORE_INIT(ClientMessage);
    msg.which_payload = WINDRPC_CLIENT_REQUEST_TAG;
    CORE_TYPE(Request) *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "tx-err-999";

    req->which_service = 99; 

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    bool ok = pb_encode(&ostream, WINDRPC_CLIENT_MESSAGE_FIELDS, &msg);
    assert(ok);
    txn.buffer.bytes_written = ostream.bytes_written;

    int32_t ret = windrpc_handle(&txn);
    assert(ret == 0); 
    assert(txn.buffer.bytes_written > 0);

    ok = decode_server_message_safely(&txn, &decode_result.server_msg.payload.response);
    assert(ok);
    assert(strcmp(decode_result.request_id, "tx-err-999") == 0);

    windrpc_response_msg_t *resp = &decode_result.server_msg.payload.response;
    assert(resp->which_service == WINDRPC_SERVICE_RESPONSE_TAG(status));
    assert(resp->service.status.code != 0);

    printf("test_unimplemented_error PASSED!\n");
}

static bool decode_common_result(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    windrpc_response_msg_t *resp = (windrpc_response_msg_t *)*arg;
    if (field->tag == WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, get_device_info)) {
        resp->service.common.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, get_device_info);
        return pb_decode_noinit(stream, WINDRPC_COMMON_DEVICE_INFO_FIELDS, &resp->service.common.result.get_device_info);
    }
    return false;
}

static bool decode_power_result(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    windrpc_response_msg_t *resp = (windrpc_response_msg_t *)*arg;
    if (field->tag == WINDRPC_SERVICE_RESPONSE_RESULT_TAG(power, read_power_info)) {
        resp->service.power.which_result = WINDRPC_SERVICE_RESPONSE_RESULT_TAG(power, read_power_info);
        return pb_decode_noinit(stream, SVC_FIELDS(power, PowerInfo), &resp->service.power.result.read_power_info);
    }
    return false;
}

static bool decode_service(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    windrpc_response_msg_t *resp = (windrpc_response_msg_t *)*arg;
    resp->which_service = field->tag;

    switch (field->tag) {
        case WINDRPC_SERVICE_RESPONSE_TAG(status): {
            resp->service.status.message.funcs.decode = decode_string_callback;
            resp->service.status.message.arg = NULL;
            return pb_decode_noinit(stream, WINDRPC_TYPES_FIELDS(Status), &resp->service.status);
        }
        case WINDRPC_SERVICE_RESPONSE_TAG(common): {
            resp->service.common.cb_result.funcs.decode = decode_common_result;
            resp->service.common.cb_result.arg = resp;
            return pb_decode_noinit(stream, WINDRPC_SERVICE_RESPONSE_FIELDS(common), &resp->service.common);
        }
        case WINDRPC_SERVICE_RESPONSE_TAG(power): {
            resp->service.power.cb_result.funcs.decode = decode_power_result;
            resp->service.power.cb_result.arg = resp;
            return pb_decode_noinit(stream, WINDRPC_SERVICE_RESPONSE_FIELDS(power), &resp->service.power);
        }
        default:
            printf("Unknown service: %d\n", field->tag);
            return false;
    }
}

static bool decode_payload(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    if (field->tag == WINDRPC_SERVER_RESPONSE_TAG) {
        windrpc_response_msg_t *resp = (windrpc_response_msg_t *)field->pData;
        resp->request_id.funcs.decode = decode_string_callback;
        resp->request_id.arg = decode_result.request_id;
        resp->cb_service.funcs.decode = decode_service;
        resp->cb_service.arg = resp;

        return pb_decode_noinit(stream, WINDRPC_CAT(WINDRPC_PACKAGE_NAME, _windrpc_core_Response_fields), resp);
    }
    return false;
}

static bool decode_server_message_safely(struct windrpc_transaction *txn, windrpc_response_msg_t *out_resp) {
    pb_istream_t stream = pb_istream_from_buffer(txn->buffer.tx_data, txn->buffer.bytes_written);
    
    CORE_TYPE(ServerMessage) resp_msg = CORE_INIT(ServerMessage);
    resp_msg.cb_payload.funcs.decode = decode_payload;
    resp_msg.cb_payload.arg = NULL;
    
    memset(&decode_result, 0, sizeof(decode_result));
    
    bool ok = pb_decode(&stream, WINDRPC_SERVER_MESSAGE_FIELDS, &resp_msg);
    if (!ok) {
        printf("[safely] pb_decode failed! Error: %s\n", PB_GET_ERROR(&stream));
    } else {
        decode_result.server_msg = resp_msg;
    }
    return ok;
}

static void test_get_device_info(void) {
    printf("Running test_get_device_info...\n");

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
#if !defined(WINDRPC_USE_INPLACE_BUFFER) || (WINDRPC_USE_INPLACE_BUFFER == 0)
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
#endif
            .bytes_written = 0
        },
        .context = {0},
        .operation = {0}
    };

    CORE_TYPE(ClientMessage) msg = CORE_INIT(ClientMessage);
    msg.which_payload = WINDRPC_CLIENT_REQUEST_TAG;
    CORE_TYPE(Request) *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "tx-devinfo-001";

    req->which_service = WINDRPC_SERVICE_REQUEST_TAG(common);
    req->service.common.which_command = WINDRPC_SERVICE_REQUEST_CMD_TAG(common, get_device_info);

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    bool ok = pb_encode(&ostream, WINDRPC_CLIENT_MESSAGE_FIELDS, &msg);
    printf("[test_get_device_info] encode ok=%d, bytes=%zu\n", ok, ostream.bytes_written);
    assert(ok);
    txn.buffer.bytes_written = ostream.bytes_written;

    printf("[test_get_device_info] calling windrpc_handle...\n");
    int32_t ret = windrpc_handle(&txn);
    printf("[test_get_device_info] handle ret=%d, tx_bytes=%u\n", ret, txn.buffer.bytes_written);
    printf("[test_get_device_info] HEX:");
    for (uint16_t i = 0; i < txn.buffer.bytes_written; i++) {
        printf(" %02X", txn.buffer.tx_data[i]);
    }
    printf("\n");
    assert(ret == 0);
    assert(txn.buffer.bytes_written > 0);

    printf("[test_get_device_info] calling decode_server_message_safely...\n");
    ok = decode_server_message_safely(&txn, &decode_result.server_msg.payload.response);
    printf("[test_get_device_info] decode ok=%d\n", ok);
    assert(ok);

    windrpc_response_msg_t *resp = &decode_result.server_msg.payload.response;
    assert(resp->which_service == WINDRPC_SERVICE_RESPONSE_TAG(common));
    assert(resp->service.common.which_result ==
           WINDRPC_SERVICE_RESPONSE_RESULT_TAG(common, get_device_info));

    SVC_TYPE(common, DeviceInfo) *info = &resp->service.common.result.get_device_info;
    assert(strcmp(info->serial_number, "SN-TEST-1234") == 0);
    assert(strcmp(info->manufacturer_name, "unknown") == 0);
    assert(strcmp(info->model_number, "unknown") == 0);
    assert(strcmp(info->hw_revision, "unknown") == 0);
    assert(strcmp(info->fw_revision, "unknown") == 0);

    printf("test_get_device_info PASSED!\n");
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("=== WindRPC Host C Test Started ===\n");

    static struct windrpc_device_info device_info = {
        .serial_number = "SN-TEST-1234"
    };
    windrpc_init(&device_info);

    test_ping();
    test_display_pixels();
    test_read_power_info();
    test_unimplemented_error();
    test_get_device_info();

    printf("=== All WindRPC Host C Tests PASSED! ===\n");
    return 0;
}
