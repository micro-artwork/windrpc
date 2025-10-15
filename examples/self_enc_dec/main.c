#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "windrpc.h"

#define COLOR_COUNT 10
#define BUFFER_SIZE 256

uint8_t buffer[BUFFER_SIZE];

// struct windrpc_buffer windrpc_buffer = {
//     .data = buffer,
//     .size = BUFFER_SIZE,
//     .bytes_written = 0,
// };

// struct windrpc_context ctx = {0};

struct windrpc_transaction txn = {
    .buffer = {
        .data = buffer,
        .size = BUFFER_SIZE,
        .bytes_written = 0,
    },
    .context = {0},
    .operation = {0}};

// ---- 요청 생성 헬퍼 함수 ----

static bool decode_request_id(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    char *str = (char *)*arg;
    size_t len = stream->bytes_left;
    if (len >= WINDRPC_REQUEST_ID_MAX_LEN) return false;
    if (!pb_read(stream, (pb_byte_t *)str, len)) return false;
    return true;
}

static bool decode_string_callback(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    // arg를 이용해 콜백 함수에 추가적인 정보를 전달할 수 있습니다.
    // 이 예제에서는 arg로 목적지 버퍼의 포인터를 전달합니다.
    // char *dest_buffer = (char *)*arg;
    char *dest_buffer = (char *)*arg;

    // 1. 수신될 문자열의 길이를 확인합니다.
    //    콜백으로 전달된 스트림은 해당 필드의 데이터만 포함합니다.
    size_t len = stream->bytes_left;
    printf("decoding string, len: %zu\n", len);

    // 2. 목적지 버퍼의 크기를 초과하는지 확인하여 오버플로우를 방지합니다.
    //    (여기서는 버퍼 크기를 64로 가정)
    if (len >= 64) {
        printf("error: string is too long\n");
        return false;
    }

    // 3. pb_read 함수를 사용하여 스트림에서 문자열 데이터를 읽습니다.
    if (!pb_read(stream, (pb_byte_t *)dest_buffer, len)) {
        printf("error decoding string: %s\n", PB_GET_ERROR(stream));
        return false;
    }

    // 4. C 스타일 문자열로 만들기 위해 마지막에 NULL 문자를 추가합니다.
    dest_buffer[len] = '\0';

    printf("decoded string: \"%s\"\n", dest_buffer);

    // 성공 시 true 반환
    return true;
}

// request_id 인코딩 콜백
static bool encode_string_callback(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    const char *str = (const char *)*arg;
    if (!pb_encode_tag_for_field(stream, field)) return false;
    return pb_encode_string(stream, (uint8_t *)str, strlen(str));
}

// colors(repeated fixed32) 인코딩 콜백
static bool encode_colors_callback(pb_ostream_t *stream, const pb_field_t *field, void *const *arg) {
    uint32_t *colors = (uint32_t *)(*arg);
    for (size_t i = 0; i < COLOR_COUNT; ++i) {
        if (!pb_encode_tag_for_field(stream, field)) return false;
        if (!pb_encode_fixed32(stream, &colors[i])) return false;
    }
    return true;
}

static void prepare_led_request(void) {
    // 1. 색상 데이터 준비
    static uint32_t color_data[COLOR_COUNT];
    for (int i = 0; i < COLOR_COUNT; ++i) {
        color_data[i] = 0x11223344 + i;
    }

    // 2. 최상위 ClientMessage 생성
    bitnari_windrpc_core_ClientMessage msg = bitnari_windrpc_core_ClientMessage_init_zero;

    // request_id 설정
    msg.which_payload = bitnari_windrpc_core_ClientMessage_request_tag;
    bitnari_windrpc_core_Request *req = &msg.payload.request;
    // msg.payload.request.request_id.funcs.encode = encode_string_callback;
    // msg.payload.request.request_id.arg = "req-led-1";

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "req-led-1";

    // 서비스 및 커맨드 설정
    req->which_service = bitnari_windrpc_core_Request_led_tag;
    req->service.led.which_command = bitnari_windrpc_service_led_Request_display_pixels_tag;
    req->service.led.command.display_pixels.colors.funcs.encode = encode_colors_callback;
    req->service.led.command.display_pixels.colors.arg = color_data;

    // 3. 인코딩
    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    if (!pb_encode(&ostream, bitnari_windrpc_core_ClientMessage_fields, &msg)) {
        printf("Encode failed: %s\n", PB_GET_ERROR(&ostream));
        txn.buffer.bytes_written = 0;
        return;
    }
    txn.buffer.bytes_written = ostream.bytes_written;
}

static void prepare_ping_request(void) {
    // windrpc_client_msg_t req = bitnari_windrpc_core_ClientMessage_init_zero;
    windrpc_client_msg_t msg = bitnari_windrpc_core_ClientMessage_init_zero;

    // request_id 설정
    msg.which_payload = bitnari_windrpc_core_ClientMessage_request_tag;
    bitnari_windrpc_core_Request *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "req-ping-1";

    // ping은 이제 common 서비스에 속합니다.
    req->which_service = bitnari_windrpc_core_Request_common_tag;
    req->service.common.which_command = bitnari_windrpc_service_common_Request_ping_tag;
    // ping 메시지는 Empty 이므로 페이로드 설정이 필요 없습니다.

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    if (!pb_encode(&ostream, bitnari_windrpc_core_ClientMessage_fields, &msg)) {
        printf("[PING] Encoding failed: %s\n", PB_GET_ERROR(&ostream));
        txn.buffer.bytes_written = 0;
        return;
    }
    txn.buffer.bytes_written = ostream.bytes_written;
}

// static void prepare_get_rpc_version_request() {
//     bitnari_windrpc_core_ClientMessage req = bitnari_windrpc_core_ClientMessage_init_zero;

//     req.request_id.funcs.encode = encode_string_callback;
//     req.request_id.arg = "req-version-1";

//     req.which_service = bitnari_windrpc_core_ClientMessage_common_tag;
//     req.service.common.which_command = bitnari_windrpc_service_common_Request_get_rpc_version_tag;

//     pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
//     if (!pb_encode(&ostream, bitnari_windrpc_core_ClientMessage_fields, &req)) {
//         printf("[GET VERSION] Encoding failed: %s\n", PB_GET_ERROR(&ostream));
//         txn.buffer.bytes_written = 0;
//         return;
//     }
//     txn.buffer.bytes_written = ostream.bytes_written;
// }

static void prepare_subscribe_power_request(void) {
    // windrpc_client_msg_t req = bitnari_windrpc_core_ClientMessage_init_zero;
    windrpc_client_msg_t msg = bitnari_windrpc_core_ClientMessage_init_zero;

    // request_id 설정
    msg.which_payload = bitnari_windrpc_core_ClientMessage_request_tag;
    bitnari_windrpc_core_Request *req = &msg.payload.request;

    req->request_id.funcs.encode = encode_string_callback;
    req->request_id.arg = "req-power-sub-1";

    req->which_service = bitnari_windrpc_core_Request_power_tag;
    req->service.power.which_command = bitnari_windrpc_service_power_Request_subscribe_power_info_tag;
    req->service.power.command.subscribe_power_info.enable = true;

    pb_ostream_t ostream = pb_ostream_from_buffer(txn.buffer.data, txn.buffer.size);
    if (!pb_encode(&ostream, bitnari_windrpc_core_ClientMessage_fields, &msg)) {
        printf("[SUBSCRIBE POWER] Encoding failed: %s\n", PB_GET_ERROR(&ostream));
        txn.buffer.bytes_written = 0;
        return;
    }
    txn.buffer.bytes_written = ostream.bytes_written;
}

// in test.c

static bool decode_service(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;

    switch (field->tag) {
        case bitnari_windrpc_core_Response_status_tag: {
            bitnari_windrpc_types_Status *msg = (bitnari_windrpc_types_Status *)field->pData;
            return pb_decode(stream, bitnari_windrpc_types_Status_fields, msg);
        }
        case bitnari_windrpc_core_Response_common_tag: {
            bitnari_windrpc_service_common_Response *msg = (bitnari_windrpc_service_common_Response *)field->pData;
            return pb_decode(stream, bitnari_windrpc_service_common_Response_fields, msg);
        }
        case bitnari_windrpc_core_Response_power_tag: {
            bitnari_windrpc_service_power_Response *msg = (bitnari_windrpc_service_power_Response *)field->pData;
            return pb_decode(stream, bitnari_windrpc_service_power_Response_fields, msg);
        }
        default:
            printf("Unknown service: %d", field->tag);
            return false;
    }
}

static bool decode_payload(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;

    switch (field->tag) {
        case bitnari_windrpc_core_ServerMessage_response_tag: {
            windrpc_response_msg_t *msg = (windrpc_response_msg_t *)field->pData;

            msg->request_id.funcs.decode = decode_string_callback;
            msg->request_id.arg = (void *)ctx->request_id;
            // msg->request_id.arg = arg;
            msg->cb_service.funcs.decode = decode_service;
            // msg->cb_service.arg = ctx;
            break;
            case bitnari_windrpc_core_ServerMessage_notification_tag: {
                printf("notification!\n");
                return false;
            }
            default:
                return false;
        }
    }

    return true;
}

// --- [수정] print_response 함수 ---
static bool decode_response_service(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    // 응답 메시지의 service oneof를 디코딩하는 콜백
    // 실제로는 각 service response 메시지를 디코딩하면 됨
    // 이 예제에서는 단순화를 위해 전체를 디코딩하지 않고 태그만 확인
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;
    // ctx->which_service = field->tag;
    return pb_decode(stream, NULL, NULL);  // 스트림을 소진시켜 다음으로 넘어감
}

static bool decode_response_submessage(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;
    windrpc_response_msg_t *resp = (windrpc_response_msg_t *)field->pData;

    resp->request_id.funcs.decode = decode_request_id;
    resp->request_id.arg = ctx;

    // 여기서는 간단히 처리하지만, 실제로는 decode_service처럼 콜백으로 처리해야 함
    // Nanopb oneof 콜백은 한 번만 설정 가능하므로, 이 방식은 제한적임.
    // 실제 응답 데이터를 제대로 파싱하려면 decode.c에서처럼 더 복잡한 콜백 체인이 필요.
    // 테스트 목적상 전체 디코딩을 다시 수행.
    return true;
}

static void print_response() {
    char status_message[64] = {0};  // 버퍼를 0으로 초기화
    char request_id[38] = {0};
    struct windrpc_context ctx = {0};

    if (txn.buffer.bytes_written == 0) {
        printf("No response message.\n");
        return;
    }

    windrpc_server_msg_t res_msg = bitnari_windrpc_core_ServerMessage_init_zero;
    pb_istream_t istream = pb_istream_from_buffer(txn.buffer.data, txn.buffer.bytes_written);

    // 응답 디코딩을 위한 request_id 콜백 설정
    // res_msg.payload.response.request_id.funcs.decode = decode_request_id;
    // res_msg.payload.response.request_id.arg = &txn.context;

    res_msg.cb_payload.funcs.decode = decode_payload;
    res_msg.cb_payload.arg = &ctx;

    // 디코딩
    if (!pb_decode(&istream, bitnari_windrpc_core_ServerMessage_fields, &res_msg)) {
        printf("Failed to decode server response message: %s\n", PB_GET_ERROR(&istream));
        return;
    }

    // if (res_msg.which_payload == bitnari_windrpc_core_ServerMessage_response_tag) {
    //     windrpc_response_msg_t *response = &res_msg.payload.response;
    //     printf("====> Received Response for request_id: %s\n", txn.context.request_id);

    //     if (response->which_service == bitnari_windrpc_core_Response_common_tag) {
    //         if (response->service.common.which_result == bitnari_windrpc_service_common_Response_ping_tag) {
    //             printf("--> Received Common::Ping response (VersionCode: %u)\n", response->service.common.result.ping);
    //         }
    //     }
    // }

    // 5. 디코딩이 완료된 후, 어떤 타입의 메시지가 수신되었는지 확인합니다.
    if (res_msg.which_payload == bitnari_windrpc_core_ServerMessage_response_tag) {
        // 6. 'response' 포인터를 이제야 안전하게 할당합니다.
        windrpc_response_msg_t *response = &res_msg.payload.response;

        // 콜백 함수에 의해 ctx.request_id가 채워졌으므로 출력합니다.
        printf("====> Received Response for request_id: %s\n", ctx.request_id);

        // 7. 이제 'response' 포인터를 안전하게 사용하여 내부 데이터를 확인할 수 있습니다.
        if (response->which_service == bitnari_windrpc_core_Response_status_tag) {
            printf("--> Received ERROR response: code=%d, message='%s'\n", response->service.status.code, status_message);
        } else if (response->which_service == bitnari_windrpc_core_Response_common_tag) {
            // if (response->service.common.which_result == bitnari_windrpc_service_common_Response_get_rpc_version_tag) {
            //     printf("--> Received Common::GetVersionCode response: version=%u\n", response->service.common.result.get_rpc_version.code);
            // } else
            if (response->service.common.which_result == bitnari_windrpc_service_common_Response_ping_tag) {
                printf("--> Received Common::Ping response (VersionCode: %u)\n", response->service.common.result.ping);
            }
        } else if (response->which_service == bitnari_windrpc_core_Response_power_tag) {
            if (response->service.power.which_result == bitnari_windrpc_service_power_Request_subscribe_power_info_tag) {
                printf("--> Received Power::Subscribe response (Empty)\n");
            }
        }

    } else if (res_msg.which_payload == bitnari_windrpc_core_ServerMessage_notification_tag) {
        printf("Received Notification (not handled in this test)\n");
    }
}

static void rpc_test(void) {
    int32_t result;

    printf("\n--------------- 1. LED Service (display_pixels) ------------\n");
    prepare_led_request();
    // result = windrpc_handle(&windrpc_buffer, &ctx);
    result = windrpc_handle(&txn);
    if (result) printf("windrpc_handle failed: %d\n", result);
    print_response();  // LED 서비스는 응답이 없어야 함

    printf("\n--------------- 2. Common Service (ping) ------------\n");
    prepare_ping_request();
    // result = windrpc_handle(&windrpc_buffer, &ctx);
    result = windrpc_handle(&txn);
    if (result) printf("windrpc_handle failed: %d\n", result);
    print_response();

    // printf("\n--------------- 3. Common Service (get_rpc_version) ------------\n");
    // prepare_get_rpc_version_request();
    // // result = windrpc_handle(&windrpc_buffer, &ctx);
    // result = windrpc_handle(&txn);
    // if (result) printf("windrpc_handle failed: %d\n", result);
    // print_response();

    printf("\n--------------- 3. Power Service (subscribe_power_info) ------------\n");
    prepare_subscribe_power_request();
    // result = windrpc_handle(&windrpc_buffer, &ctx);
    result = windrpc_handle(&txn);
    if (result) printf("windrpc_handle failed: %d\n", result);
    print_response();
}

/* -------------------------------------------------------------------------- */
/* windrpc 서비스 구현                           */
/* -------------------------------------------------------------------------- */

struct pixel_data {
    uint32_t colors[255];
    size_t count;
};

struct pixel_data pixel = {0};

// --- LED 서비스 구현 ---
static bool decode_colors(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    struct windrpc_context *ctx = (struct windrpc_context *)*arg;
    // struct pixel_data *data = &ctx->arg.pixel;
    uint32_t value;
    struct pixel_data *data = &pixel;

    // 이 콜백은 repeated 필드의 각 아이템에 대해 호출됩니다.
    // 여기서는 packed=true를 가정하고 스트림의 끝까지 디코딩합니다.
    while (stream->bytes_left > 0 && data->count < 255) {
        if (!pb_decode_fixed32(stream, &value)) {
            printf("Decode failed: %s\n", PB_GET_ERROR(stream));
            return false;
        }
        data->colors[data->count++] = value;
    }
    return true;
}

// static bool decode_display_pixels(pb_istream_t *stream, const pb_field_t *field, void **arg) {
//     bitnari_windrpc_service_led_PixelData *msg = field->pData;
//     msg->colors.funcs.decode = decode_colors;
//     msg->colors.arg = *arg;
//     return true;
// }

static bool decode_display_pixels(pb_istream_t *stream, const pb_field_t *field, void **arg) {
    // 이 함수는 display_pixels(PixelData) 메시지를 디코딩하기 위해 호출됩니다.
    bitnari_windrpc_service_led_PixelData msg = bitnari_windrpc_service_led_PixelData_init_zero;
    // PixelData 메시지 내의 'colors' 필드를 디코딩할 때 'decode_colors' 콜백을 사용하도록 설정합니다.
    msg.colors.funcs.decode = decode_colors;
    msg.colors.arg = *arg;

    // PixelData 메시지 자체를 디코딩합니다. 이 과정에서 Nanopb는 내부적으로 decode_colors를 호출합니다.
    if (!pb_decode(stream, bitnari_windrpc_service_led_PixelData_fields, &msg)) {
        printf("Failed to decode PixelData submessage: %s\n", PB_GET_ERROR(stream));
        return false;
    }
    return true;
}

static int32_t execute_display_pixels(struct windrpc_operation *operation, void *context) {
    struct windrpc_context *ctx = (struct windrpc_context *)context;

    // size_t count = ctx->arg.pixel.count;
    // uint32_t *colors = ctx->arg.pixel.colors;
    size_t count = pixel.count;
    uint32_t *colors = pixel.colors;

    printf("Execute: display_pixels, color count: %zu\n", count);
    for (size_t i = 0; i < count; ++i) {
        printf("  - Color[%zu]: 0x%08X\n", i, colors[i]);
    }
    return 0;  // 성공
}

static struct windrpc_service_led led_service = {
    // .decode_display_pixels = decode_display_pixels,
    // .execute_display_pixels = execute_display_pixels,
    .display_pixels = {
        .decode_cmd = decode_display_pixels,
        .encode_res = NULL,
        .execute = execute_display_pixels,
    }};

// --- Power 서비스 구현 ---
static int32_t execute_subscribe_power_info(struct windrpc_operation *operation, void *context) {
    windrpc_request_msg_t *request = &operation->client_msg.payload.request;
    // 이제 request 포인터를 통해 직접 데이터에 접근
    printf("Execute: subscribe_power_info, enable=%d\n", request->service.power.command.subscribe_power_info.enable);
    return 0;
}

static void encode_subscribe_power_info(windrpc_response_msg_t *response, void *context) {
    response->service.power.which_result = bitnari_windrpc_service_power_Request_subscribe_power_info_tag;
    // 응답 페이로드는 Empty이므로 추가 설정 불필요
}

static struct windrpc_service_power power_service = {
    // .execute_subscribe_power_info = execute_subscribe_power_info,
    // .encode_subscribe_power_info = encode_subscribe_power_info,
    .subscribe_power_info = {
        .decode_cmd = NULL,
        .encode_res = encode_subscribe_power_info,
        .execute = execute_subscribe_power_info,
    }};

// --- 최상위 서비스 등록 ---
struct windrpc_user_service windrpc_services = {
    // .common = &common_service,
    .led = &led_service,
    .power = &power_service,
};

int main(void) {
    printf("--- windrpc test started ---\n");
    windrpc_init(&windrpc_services);
    rpc_test();
    printf("\n--- windrpc test finished ---\n");
    return 0;
}