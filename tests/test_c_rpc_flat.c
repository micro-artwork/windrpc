#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "windrpc.h"

#define BUFFER_SIZE 512
static uint8_t shared_buffer[BUFFER_SIZE];
static uint8_t shared_tx_buffer[BUFFER_SIZE];

#define SVC_TYPE(svc, t) WINDRPC_CAT5(WINDRPC_PACKAGE_NAME, _windrpc_service_, svc, _, t)

// Mock 서비스 실행 상태 저장용 전역 변수
static struct {
    int display_pixels_called;
    int read_power_info_called;
} mock_state;

int32_t execute_display_pixels(const SVC_TYPE(led, PixelData) *req, void *context) {
    (void)req;
    (void)context;
    mock_state.display_pixels_called++;
    return 0;
}

int32_t execute_read_power_info(const rpc_types_Empty_t *req, rpc_power_PowerInfo_t *res, void *context) {
    (void)req;
    (void)context;
    mock_state.read_power_info_called++;
    if (res) {
        res->voltage_mill = 3300;
        res->ampere_mill = 500;
        res->watt_mill = 1650;
    }
    return 0;
}

int32_t execute_subscribe_power_notification(const rpc_types_Subscribe_t *req, rpc_types_Empty_t *res, void *context) {
    (void)req;
    (void)res;
    (void)context;
    return 0;
}

int main(void) {
    printf("--- Running Flat Envelope Mode C Unit Tests ---\n");

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
            .bytes_written = 0,
            .tx_data = shared_tx_buffer,
            .tx_size = BUFFER_SIZE,
        }
    };

    windrpc_init(NULL);

    // Test ping RPC (0x0601)
    shared_buffer[0] = 0x06;
    shared_buffer[1] = 0x01;
    shared_buffer[2] = 0x00;
    shared_buffer[3] = 0x01; // seq_id = 1
    shared_buffer[4] = 0;    // payload_len = 0
    txn.buffer.bytes_written = 5;

    int32_t err = windrpc_handle(&txn);
    assert(err == 0);
    assert(txn.buffer.bytes_written > 5);
    printf("PASS: Flat Ping RPC Test\n");

    printf("ALL FLAT C UNIT TESTS PASSED SUCCESSFULLY!\n");
    return 0;
}
