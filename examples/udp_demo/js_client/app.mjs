/* =========================================================================
 * USER-WRITTEN FILE: Node.js UDP Client Application
 * =========================================================================
 * Connects to C UDP Server on 127.0.0.1:5000.
 * Demonstrates 6-byte header raw datagram RPC requests & server push events.
 */

import dgram from 'dgram';
import {
    WindRpcClient,
    RPC_ID,
    decodePowerstatus,
    encodeLedcolor,
    decodeLedresult,
    decodePingresponse
} from './generated/WindRpcClient.js';

const SERVER_HOST = '127.0.0.1';
const SERVER_PORT = 5000;

const socket = dgram.createSocket('udp4');
const client = new WindRpcClient();

// Helper to send frame over UDP
const transportSend = (frame) => {
    socket.send(frame, SERVER_PORT, SERVER_HOST);
};

// Handle incoming UDP datagrams
socket.on('message', (msg) => {
    client.receiveRawDatagram(msg, (notification) => {
        const { rpcId, payload } = notification;

        // Server Push Notification (0x0882 - charging_alert)
        if (rpcId === RPC_ID.POWER_MANAGER_CHARGING_ALERT) {
            const alert = decodePowerstatus(payload);
            console.log('\n[JS-CLIENT][NOTIFICATION-EVENT ⚡] Charging Alert Received!');
            console.log(`  -> Voltage: ${alert.voltage_mv} mV, Current: ${alert.current_ma} mA, Charging: ${alert.is_charging}`);
        }
    });
});

async function main() {
    console.log('============================================================');
    console.log(' Node.js WindRPC UDP Client Running');
    console.log('============================================================');

    try {
        // Step 1: Ping Core Handshake (0x0601)
        console.log('\n[JS-CLIENT][TX] Step 1: Sending Core Ping (0x0601)...');
        const pingFrame = await client.sendRequest(RPC_ID.COMMON_PING, new Uint8Array(0), transportSend, 2000);
        const pingInfo = decodePingresponse(pingFrame.payload);
        console.log(`[JS-CLIENT][RX] Handshake Verified! Core: ${pingInfo.core_version_name}, Spec: ${pingInfo.spec_version_name}`);

        // Step 2: Request Power Status (0x0801)
        console.log('\n[JS-CLIENT][TX] Step 2: Calling get_power_status (0x0801)...');
        const powerFrame = await client.sendRequest(RPC_ID.POWER_MANAGER_GET_POWER_STATUS, new Uint8Array(0), transportSend, 2000);
        const status = decodePowerstatus(powerFrame.payload);
        console.log(`[JS-CLIENT][RX] PowerStatus: ${status.voltage_mv} mV, ${status.current_ma} mA, Charging: ${status.is_charging}`);

        // Step 3: Set LED Color (0x0901)
        console.log('\n[JS-CLIENT][TX] Step 3: Calling set_led_color (0x0901) -> RGB(255, 128, 0)...');
        const ledReqPayload = encodeLedcolor({ r: 255, g: 128, b: 0 });
        const ledFrame = await client.sendRequest(RPC_ID.DEVICE_CONTROL_SET_LED_COLOR, ledReqPayload, transportSend, 2000);
        const ledRes = decodeLedresult(ledFrame.payload);
        console.log(`[JS-CLIENT][RX] LedResult -> Success: ${ledRes.success}`);

        // Wait a short moment to receive the server push notification from C Server
        await new Promise(r => setTimeout(r, 1000));

    } catch (err) {
        console.error('[JS-CLIENT][ERROR]', err.message);
    } finally {
        socket.close();
        console.log('\n[JS-CLIENT] Execution finished cleanly.');
    }
}

main();
