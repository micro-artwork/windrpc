# =========================================================================
# USER-WRITTEN FILE: Python UDP Client Application
# =========================================================================
# Connects to C UDP Server on 127.0.0.1:5000.
# Demonstrates 6-byte header raw datagram RPC requests & server push events in Python.

import sys
import os
import socket
import asyncio

# Bypass Protobuf gencode/runtime version check if protoc version differs from python package version
try:
    import google.protobuf.runtime_version
    google.protobuf.runtime_version.ValidateProtobufRuntimeVersion = lambda *args, **kwargs: None
except ImportError:
    pass

# Import generated WindRpcClient SDK and Protobuf Data Classes
demo_py_dir = os.path.dirname(os.path.abspath(__file__))
gen_dir = os.path.join(demo_py_dir, "generated")
sys.path.insert(0, gen_dir)
sys.path.insert(0, os.path.join(gen_dir, "Generated"))

from WindRpcClient import (
    WindRpcClient,
    RPC_COMMON_PING,
    RPC_POWER_MANAGER_GET_POWER_STATUS,
    RPC_POWER_MANAGER_CHARGING_ALERT,
    RPC_DEVICE_CONTROL_SET_LED_COLOR
)
from device_demo.windrpc.service import common_pb2, power_manager_pb2, device_control_pb2

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000


class UdpClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, client_sdk, on_notify_cb):
        self.client_sdk = client_sdk
        self.on_notify_cb = on_notify_cb
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.client_sdk.receive_raw_datagram(data, on_notification=self.on_notify_cb)


def handle_notification(frame):
    if frame.rpc_id == RPC_POWER_MANAGER_CHARGING_ALERT:
        alert = power_manager_pb2.PowerStatus()
        alert.ParseFromString(frame.payload)
        print("\n[PY-CLIENT][NOTIFICATION-EVENT ⚡] Charging Alert Received!")
        print(f"  -> Voltage: {alert.voltage_mv} mV, Current: {alert.current_ma} mA, Charging: {alert.is_charging}")


async def main():
    print("============================================================")
    print(" Python WindRPC UDP Client Running")
    print("============================================================")

    client = WindRpcClient()
    loop = asyncio.get_running_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UdpClientProtocol(client, handle_notification),
        remote_addr=(SERVER_HOST, SERVER_PORT)
    )

    def transport_send(frame):
        transport.sendto(frame)

    try:
        # Step 1: Ping Core Handshake (0x0601)
        print("\n[PY-CLIENT][TX] Step 1: Sending Core Ping (0x0601)...")
        ping_frame = await client.send_request_async(RPC_COMMON_PING, b"", transport_send, timeout_ms=2000)
        ping_res = common_pb2.PingResponse()
        ping_res.ParseFromString(ping_frame.payload)
        print(f"[PY-CLIENT][RX] Handshake Verified! Core: {ping_res.core_version_name}, Spec: {ping_res.spec_version_name}")

        # Step 2: Request Power Status (0x0801)
        print("\n[PY-CLIENT][TX] Step 2: Calling get_power_status (0x0801)...")
        power_frame = await client.send_request_async(RPC_POWER_MANAGER_GET_POWER_STATUS, b"", transport_send, timeout_ms=2000)
        status = power_manager_pb2.PowerStatus()
        status.ParseFromString(power_frame.payload)
        print(f"[PY-CLIENT][RX] PowerStatus: {status.voltage_mv} mV, {status.current_ma} mA, Charging: {status.is_charging}")

        # Step 3: Set LED Color (0x0901)
        print("\n[PY-CLIENT][TX] Step 3: Calling set_led_color (0x0901) -> RGB(0, 255, 128)...")
        led_req = device_control_pb2.LedColor(r=0, g=255, b=128)
        led_frame = await client.send_request_async(RPC_DEVICE_CONTROL_SET_LED_COLOR, led_req.SerializeToString(), transport_send, timeout_ms=2000)
        led_res = device_control_pb2.LedResult()
        led_res.ParseFromString(led_frame.payload)
        print(f"[PY-CLIENT][RX] LedResult -> Success: {led_res.success}")

        # Wait a short moment for notification
        await asyncio.sleep(1.0)

    except Exception as e:
        print(f"[PY-CLIENT][ERROR] {e}")
    finally:
        transport.close()
        print("\n[PY-CLIENT] Execution finished cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
