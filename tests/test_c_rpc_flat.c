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

int32_t windrpc_on_display_pixels(const SVC_TYPE(led, PixelData) *req, void *context) {
    (void)req;
    (void)context;
    mock_state.display_pixels_called++;
    return 0;
}

int32_t windrpc_on_read_power_info(const rpc_types_Empty_t *req, rpc_power_PowerInfo_t *res, void *context) {
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

int32_t windrpc_on_subscribe_power_notification(const rpc_types_Subscribe_t *req, rpc_types_Empty_t *res, void *context) {
    (void)req;
    (void)res;
    (void)context;
    return 0;
}

int main(void) {
#if defined(WINDRPC_USE_INPLACE_BUFFER) && WINDRPC_USE_INPLACE_BUFFER == 1
    printf("--- Running Flat C Unit Tests [IN-PLACE BUFFER MODE] ---\n");
    uint8_t *tx_buf = shared_buffer;
#else
    printf("--- Running Flat C Unit Tests [DOUBLE BUFFER MODE] ---\n");
    uint8_t *tx_buf = shared_tx_buffer;
#endif

    struct windrpc_transaction txn = {
        .buffer = {
            .data = shared_buffer,
            .size = BUFFER_SIZE,
            .bytes_written = 0,
            .tx_data = tx_buf,
            .tx_size = BUFFER_SIZE,
        }
    };

    windrpc_init(NULL);

    // Test ping RPC (0x0601)
    shared_buffer[0] = 0x01; // rpc_id lo
    shared_buffer[1] = 0x06; // rpc_id hi
    shared_buffer[2] = 0x01; // seq_id lo
    shared_buffer[3] = 0x00; // seq_id hi
    shared_buffer[4] = 0;    // payload_len_lo = 0
    shared_buffer[5] = 0;    // payload_len_hi = 0
    txn.buffer.bytes_written = 6;

    int32_t err = windrpc_handle(&txn);
    assert(err == 0);
    assert(txn.buffer.bytes_written > 6);
    assert(tx_buf[0] == 0x01 && tx_buf[1] == 0x06);
    printf("PASS: Flat Ping RPC Test\n");

    // Test get_device_info RPC (0x0602)
    shared_buffer[0] = 0x02; // rpc_id lo
    shared_buffer[1] = 0x06; // rpc_id hi
    shared_buffer[2] = 0x02; // seq_id lo
    shared_buffer[3] = 0x00; // seq_id hi
    shared_buffer[4] = 0;    // payload_len_lo = 0
    shared_buffer[5] = 0;    // payload_len_hi = 0
    txn.buffer.bytes_written = 6;

    int32_t err_dev_info = windrpc_handle(&txn);
    assert(err_dev_info == 0);
    assert(txn.buffer.bytes_written > 6);
    assert(tx_buf[0] == 0x02 && tx_buf[1] == 0x06);
    printf("PASS: Flat Get Device Info RPC (0x0602) Test\n");

    // Test System Error Status Response (Unknown RPC ID 0x9999)
    shared_buffer[0] = 0x99;
    shared_buffer[1] = 0x99;
    shared_buffer[2] = 0x07; // seq_id = 7
    shared_buffer[3] = 0x00;
    shared_buffer[4] = 0;
    shared_buffer[5] = 0;
    txn.buffer.bytes_written = 6;

    int32_t err_unknown = windrpc_handle(&txn);
    assert(err_unknown == 0);
    assert(txn.buffer.bytes_written >= 6);
    assert(tx_buf[0] == 0x00 && tx_buf[1] == 0x00); // System Error RPC ID = 0x0000
    assert(tx_buf[2] == 0x07 && tx_buf[3] == 0x00); // seq_id = 7
    printf("PASS: Flat System Error Status 0x0000 Response Test\n");

    printf("ALL FLAT C UNIT TESTS PASSED SUCCESSFULLY!\n");
    return 0;
}
