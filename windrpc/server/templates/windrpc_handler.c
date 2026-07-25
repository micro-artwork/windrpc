/**
 * @file windrpc_handler.c
 * @brief Auto-generated Server Handler Runner Skeleton for WindRPC (--WINDRPC_RTOS_NAME).
 * @note Adapt and incorporate this file into your RTOS task scheduler.
 */

#include "windrpc.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <stdio.h>

LOG_MODULE_REGISTER(windrpc_handler, LOG_LEVEL_INF);

// --WINDRPC_STACK_AND_BUFFER_DEFINES

#if defined(CONFIG_ZEPHYR_RTOS) || defined(__ZEPHYR__)

/* ========================================================================== */
/*                      Zephyr RTOS Thread & Queue Definitions                */
/* ========================================================================== */

struct rpc_rx_frame {
    uint16_t len;
    uint8_t data[WINDRPC_MAX_BUFFER_SIZE];
};

K_MSGQ_DEFINE(rpc_rx_msgq, sizeof(struct rpc_rx_frame), 5, 4);

/**
 * @brief Main RPC Handler Thread. Receives data from queue, decodes COBS,
 *        executes flat RPC commands, and dispatches responses.
 */
void rpc_handler_thread(void *p1, void *p2, void *p3) {
    ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(p3);

    static uint8_t rx_raw_buf[WINDRPC_MAX_BUFFER_SIZE];
    static uint8_t tx_raw_buf[WINDRPC_MAX_BUFFER_SIZE];
    static struct rpc_rx_frame frame;

    static struct windrpc_transaction txn = {
        .buffer = {
            .data = rx_raw_buf,
            .size = sizeof(rx_raw_buf),
            .bytes_written = 0,
            .tx_data = tx_raw_buf,
            .tx_size = sizeof(tx_raw_buf)
        },
        .context = {0}
    };

    static struct windrpc_device_info device_info = {
        .serial_number = "WINDRPC-ZEPHYR-001" // TODO: Set your hardware UID string here
    };

    windrpc_init(&device_info);
    LOG_INF("WindRPC Zephyr Handler Thread Started (Stack: %d B, Buffer: %d B)",
            WINDRPC_RECOMMENDED_STACK_SIZE, WINDRPC_MAX_BUFFER_SIZE);

    while (1) {
        // 1. Wait for RX Frame from Communication Driver (UART/CDC/BLE)
        if (k_msgq_get(&rpc_rx_msgq, &frame, K_FOREVER) != 0) {
            continue;
        }

        // TODO: Perform COBS decoding from frame.data into txn.buffer.data
        // uint16_t decoded_len = cobs_decode(txn.buffer.data, frame.data, frame.len);
        // txn.buffer.bytes_written = decoded_len;

        LOG_DBG("[RX] Received RPC Frame (Len: %u)", frame.len);

        // 2. Execute RPC Transaction
        int32_t err = windrpc_handle(&txn);

        // 3. Dispatch Response if generated
        if (!err && txn.buffer.bytes_written > 0) {
            LOG_DBG("[TX] Sending Response Frame (Len: %u)", txn.buffer.bytes_written);
            // TODO: COBS encode txn.buffer.tx_data and send to UART/USB TX driver
            // dispatch_tx_message(txn.buffer.tx_data, txn.buffer.bytes_written);
        }
    }
}

K_THREAD_DEFINE(rpc_handler_tid, WINDRPC_RECOMMENDED_STACK_SIZE,
                rpc_handler_thread, NULL, NULL, NULL,
                7, 0, 0);

#else

/* ========================================================================== */
/*                      Generic / FreeRTOS Skeleton Fallback                  */
/* ========================================================================== */

void rpc_handler_thread(void *arg) {
    LOG_INF("WindRPC Generic Handler Started");
    while (1) {
        // Generic handler loop implementation
    }
}

#endif
