/**
 * @file windrpc_handler.c
 * @brief Pure Transport-Agnostic Core Framework Adapter for WindRPC.
 */

#include "windrpc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// --WINDRPC_STACK_AND_BUFFER_DEFINES

/* ========================================================================== */
/*               Transport-Agnostic Raw Packet Processing Adapter             */
/* ========================================================================== */

/**
 * @brief Feeds a raw, unencoded RPC binary packet (already decoded from transport framing like COBS/GATT)
 *        directly into WindRPC engine, executes RPC handler, and outputs unencoded response packet.
 *
 * @param rx_packet Raw unencoded RPC packet bytes [RPC_ID (2B) | SEQ_ID (2B) | LEN (1B) | PAYLOAD]
 * @param rx_len Byte length of rx_packet
 * @param type Transport type source / identifier
 * @param out_resp_buf Buffer to store raw unencoded response packet (if generated)
 * @param max_resp_len Capacity of out_resp_buf
 * @param out_resp_len Out parameter receiving actual response byte length (0 if no response)
 * @return 0 on successful processing, negative error code on failure
 */
int32_t windrpc_process_packet(const uint8_t *rx_packet, uint16_t rx_len, uint32_t transport_id,
			      uint8_t *out_resp_buf, uint16_t max_resp_len, uint16_t *out_resp_len)
{
	if (!rx_packet || rx_len < 5) {
		if (out_resp_len) *out_resp_len = 0;
		return -1;
	}

	static uint8_t tx_raw_buf[WINDRPC_MAX_BUFFER_SIZE];

	struct windrpc_transaction txn;
	memset(&txn, 0, sizeof(txn));
	txn.buffer.data = (uint8_t *)rx_packet;
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
