/* =========================================================================
 * USER-WRITTEN FILE: UDP Server Entrypoint & Transport Binding
 * =========================================================================
 * Cross-platform UDP socket server listening on 127.0.0.1:5000.
 * Injects raw UDP datagram packets into windrpc_handle(&txn).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  typedef int socklen_t;
#else
  #include <unistd.h>
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  #define SOCKET int
  #define INVALID_SOCKET -1
  #define SOCKET_ERROR -1
  #define closesocket close
#endif

#include "windrpc.h"

#define UDP_PORT 5000
#define BUFFER_SIZE 1024

int main(void) {
#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        printf("!! WSAStartup failed\n");
        return 1;
    }
#endif

    SOCKET server_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (server_fd == INVALID_SOCKET) {
        printf("!! Socket creation failed\n");
        return 1;
    }

    struct sockaddr_in server_addr, client_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    server_addr.sin_port = htons(UDP_PORT);

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        printf("!! Bind failed on port %d\n", UDP_PORT);
        closesocket(server_fd);
        return 1;
    }

    printf("============================================================\n");
    printf(" WindRPC C UDP Server Listening on 127.0.0.1:%d\n", UDP_PORT);
    printf("============================================================\n");

    uint8_t rx_buf[BUFFER_SIZE];
    uint8_t tx_buf[BUFFER_SIZE];

    while (1) {
        socklen_t client_len = sizeof(client_addr);
        int bytes_received = recvfrom(server_fd, (char *)rx_buf, sizeof(rx_buf), 0,
                                      (struct sockaddr *)&client_addr, &client_len);

        if (bytes_received <= 0) continue;

        // Extract 6-byte header info for logging
        uint16_t rpc_id = (uint16_t)(rx_buf[0] | (rx_buf[1] << 8));
        uint16_t seq_id = (uint16_t)(rx_buf[2] | (rx_buf[3] << 8));
        uint16_t len    = (uint16_t)(rx_buf[4] | (rx_buf[5] << 8));

        printf("\n[C-SERVER-RX] Packet %d bytes received | RPC_ID: 0x%04X, SEQ: %u, LEN: %u\n",
               bytes_received, rpc_id, seq_id, len);

        // Bind incoming packet to WindRPC Transaction
        struct windrpc_transaction txn = {
            .buffer = {
                .data = rx_buf,
                .size = (size_t)bytes_received,
                .bytes_written = (uint16_t)bytes_received,
                .tx_data = tx_buf,
                .tx_size = sizeof(tx_buf)
            }
        };

        // Dispatch frame in WindRPC C Server Engine
        int32_t status = windrpc_handle(&txn);

        // Send response frame if produced
        if (status == 0 && txn.buffer.bytes_written > 0) {
            uint16_t tx_rpc_id = (uint16_t)(tx_buf[0] | (tx_buf[1] << 8));
            uint16_t tx_seq_id = (uint16_t)(tx_buf[2] | (tx_buf[3] << 8));
            uint16_t tx_len    = (uint16_t)(tx_buf[4] | (tx_buf[5] << 8));

            sendto(server_fd, (const char *)txn.buffer.tx_data, txn.buffer.bytes_written, 0,
                   (struct sockaddr *)&client_addr, client_len);

            printf("[C-SERVER-TX] Sent Response | RPC_ID: 0x%04X, SEQ: %u, LEN: %u\n",
                   tx_rpc_id, tx_seq_id, tx_len);
        }

        // Demonstrate Server Push Notification (charging_alert: 0x0882) right after get_power_status (0x0801)
        if (rpc_id == 0x0801) {
            printf("[C-SERVER-PUSH] Triggering Server Push Notification (charging_alert)... \n");
            rpc_power_manager_PowerStatus_t alert_data = {
                .voltage_mv = 3300,
                .current_ma = 450,
                .is_charging = true
            };

            // Reset txn tx buffer for notification
            txn.buffer.bytes_written = 0;
            if (windrpc_notify_charging_alert(&alert_data, &txn) == 0 && txn.buffer.bytes_written > 0) {
                sendto(server_fd, (const char *)txn.buffer.tx_data, txn.buffer.bytes_written, 0,
                       (struct sockaddr *)&client_addr, client_len);
                printf("[C-SERVER-PUSH] Sent Notification Packet | RPC_ID: 0x0882, LEN: %u\n",
                       txn.buffer.bytes_written - 6);
            }
        }
    }

    closesocket(server_fd);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
