# WindRPC Unified Reference Manual

This document serves as the single unified reference manual for WindRPC, covering specification guidelines (`user_spec.yml`), binary header mechanics, C server engine integration, client SDK usage (JS/TS & C#), and CLI commands.

---

## Table of Contents

1. [Overview & Highlights](#1-overview--highlights)
2. [Specification Guide (`user_spec.yml`)](#2-specification-guide-user_specyml)
   - [2.1 File Structure](#21-file-structure)
   - [2.2 Naming Rules & Styling Guide](#22-naming-rules--styling-guide)
   - [2.3 Service IDs & RPC Types](#23-service-ids--rpc-types)
   - [2.4 Static Memory Design (NanoPB Options)](#24-static-memory-design-nanopb-options)
   - [2.5 Specification Template](#25-specification-template)
3. [Architecture & Binary Protocol Mechanics](#3-architecture--binary-protocol-mechanics)
   - [3.1 6-Byte Binary Header Frame Specification](#31-6-byte-binary-header-frame-specification)
   - [3.2 16-Bit Combined RPC Identifiers](#32-16-bit-combined-rpc-identifiers)
   - [3.3 Transport Layer Responsibility & COBS Utilities](#33-transport-layer-responsibility--cobs-utilities)
   - [3.4 Buffer Isolation Modes (Double Buffering vs In-place)](#34-buffer-isolation-modes-double-buffering-vs-in-place)
   - [3.5 Core Version Handshake (`PingResponse`)](#35-core-version-handshake-pingresponse)
   - [3.6 Multi-Client & Multi-Channel Considerations](#36-multi-client--multi-channel-considerations)
4. [C Server Engine Integration](#4-c-server-engine-integration)
   - [4.1 Server Handler Callbacks](#41-server-handler-callbacks)
   - [4.2 Event Loop Binding](#42-event-loop-binding)
   - [4.3 Build Rules & Concurrency](#43-build-rules--concurrency)
5. [Client SDK Integration (JS/TS & C#)](#5-client-sdk-integration-jsts--c)
   - [5.1 JavaScript / TypeScript SDK (Node.js & Electron)](#51-javascript--typescript-sdk-nodejs--electron)
   - [5.2 C# WinForms / .NET SDK](#52-c-winforms--net-sdk)
6. [CLI Command Reference](#6-cli-command-reference)

---

## 1. Overview & Highlights

WindRPC is a zero-heap, lightweight Remote Procedure Call (RPC) framework designed for microcontrollers and cross-platform clients (Electron, C# WinForms).

- **Zero-Heap Static Memory**: 100% static allocation without dynamic memory (`malloc`/`free`), ensuring long-term MCU system stability.
- **6-Byte Binary Header**: Direct coupling of a 6-byte raw binary header and Protobuf payload, enabling $O(1)$ direct lookup dispatching.
- **Single YAML Code Generation**: Generates Protobuf schemas, Nanopb C server code, JS/TS SDK, and C# SDK from a single `user_spec.yml` file.
- **Transport Independence**: Transport framing (COBS) can be enabled, and optional application-level integrity checks (CRC) can be appended if required.

---

## 2. Specification Guide (`user_spec.yml`)

### 2.1 File Structure

A `user_spec.yml` file consists of three key areas: package namespace (`package`), metadata info (`info`), and service definitions (`services`).

```yaml
package: my_project

info:
  title: "My Control Specification"
  version: "1.0.0"
  version_code: 10000
  version_name: "1.0.0"

services:
  # Service and RPC definitions
```

> **Filename Flexibility**: `user_spec.yml` is used as an example filename. Custom names like `bitnari_spec.yml` can be passed to the CLI using `-s <your_spec_file>.yml`.

### 2.2 Naming Rules & Styling Guide

The specification validator (`spec_validator.py`) enforces the following naming rules (`^[a-zA-Z_][a-zA-Z0-9_]*$`):

| Target | Style | Applied Regex | Valid Example | Invalid Example |
| :--- | :--- | :--- | :--- | :--- |
| **package** | `snake_case` | `^[a-z][a-z0-9_]*$` | `my_project` | `my-project`, `MyProject` |
| **Service** | `snake_case` | `^[a-z][a-z0-9_]*$` | `power`, `led_control` | `PowerService`, `led-control` |
| **Message** | `PascalCase` | `^[A-Z][a-zA-Z0-9]*$` | `PowerInfo`, `PixelData` | `power_info`, `pixelData` |
| **Enum** | `PascalCase` | `^[A-Z][a-zA-Z0-9]*$` | `LedColor`, `DeviceStatus` | `led_color`, `status` |
| **Enum Member** | `UPPER_SNAKE_CASE` | `^[A-Z0-9_]+$` | `COLOR_RED`, `NONE` | `ColorRed`, `color_red` |
| **RPC Method** | `snake_case` | `^[a-z0-9_]+$` | `read_power_info` | `ReadPower`, `read-power` |
| **Field** | `snake_case` | `^[a-z0-9_]+$` | `voltage_mv` | `voltageMv`, `Voltage_Mv` |

### 2.3 Service IDs & RPC Types

- **Service ID Reservations**: **Service IDs 1 through 6 are reserved** for WindRPC core framework functions. User-defined services must use integer IDs between **7 and 255**.
- **Reserved Combined RPC IDs**:
  - `0x0000` — System Error response (reserved across all services)
  - `0x0601` — Core Ping / Version Handshake (built-in, always available)
- **RPC Types (`type`)**:
  1. `REQUEST_ONLY`: Fire-and-forget request with no server response. Requires `request`.
  2. `REQUEST_RESPONSE`: Standard bi-directional RPC. Requires `request` and `response`.
  3. `NOTIFICATION`: Server-pushed asynchronous event. Requires `event`.

### 2.4 Static Memory Design (NanoPB Options)

Message fields can specify `nanopb:` limits. Omitted options fallback to safe defaults (`string`/`bytes`: 64 bytes, `repeated`: 16 elements):

```yaml
fields:
  - number: 1
    name: colors
    type: PixelColor
    property: repeated
    nanopb: { max_count: 64 } # Limit array size statically to 64
```

### 2.5 Specification Template

```yaml
package: my_project

info:
  title: "My Control Specification"
  version: "1.0.0"
  version_code: 10000
  version_name: "1.0.0"

services:
  - id: 7
    name: led_control
    messages:
      - name: PixelColor
        fields:
          - { number: 1, name: r, type: uint32 }
          - { number: 2, name: g, type: uint32 }
          - { number: 3, name: b, type: uint32 }
      - name: PixelData
        fields:
          - number: 1
            name: colors
            type: PixelColor
            property: repeated
            nanopb: { max_count: 64 }
    rpcs:
      - id: 1
        name: display_pixels
        type: REQUEST_ONLY
        request: PixelData

  - id: 8
    name: power_manager
    messages:
      - name: PowerStatus
        fields:
          - { number: 1, name: voltage_mv, type: uint32 }
          - { number: 2, name: is_charging, type: bool }
    rpcs:
      - id: 1
        name: get_power_status
        type: REQUEST_RESPONSE
        request: types.Empty
        response: PowerStatus
      - id: 2
        name: charging_alert
        type: NOTIFICATION
        event: PowerStatus
```

---

## 3. Architecture & Binary Protocol Mechanics

### 3.1 6-Byte Binary Header Frame Specification

WindRPC combines a 6-byte raw binary header (Little-Endian) directly with Protobuf payload bytes:

```text
+-------------------+-------------------+-------------------+--------------------------------+
|  RPC_ID (2 Bytes) |  SEQ_ID (2 Bytes) | PAYLOAD_LEN (2B)  |   PAYLOAD (Protobuf Binary)    |
+-------------------+-------------------+-------------------+--------------------------------+
|     0x03 0x07     |     0x01 0x00     |    0x00 0x02      |  [NanoPB-encoded Data Bytes]   |
+-------------------+-------------------+-------------------+--------------------------------+
  |<-------------- 6-Byte Fixed Raw Binary Header (Little-Endian) ------------->|
```

- `RPC_ID` (2B, Little-Endian): `(service_id << 8) | rpc_id`
- `SEQ_ID` (2B, Little-Endian): Sequence / transaction counter (`uint16_t`)
- `PAYLOAD_LEN` (2B, Little-Endian): Protobuf payload length in bytes

### 3.2 16-Bit Combined RPC Identifiers

$$\text{combined\_id} = (\text{service\_id} \ll 8) \mid \text{rpc\_id}$$

### 3.3 Transport Layer Responsibility & COBS Utilities

WindRPC intentionally leaves data-link-level responsibilities (such as complex framing protocols and CRC/checksum calculation) to the user's application transport wrapper to avoid framework bloat on microcontrollers:

- **Data-Link Responsibilities Left to User**: CRC algorithms and link-layer protocol stacks are not built into WindRPC. In noisy hardware environments (e.g. industrial RS-485), developers can optionally calculate and append CRC16/CRC32 in their custom transport wrapper layer.
- **Client SDK COBS Utilities**: Auto-generated JS/TS, C#, and Python client SDKs include built-in COBS encoding/decoding utilities (`0x00` frame delimiter) for continuous serial streams.
- **C MCU Server COBS Integration**: The C MCU server engine (`windrpc.c`) is stateless and does not include built-in COBS logic. Developers can refer to the Zephyr-targeted C COBS reference implementation logic ([micro-artwork/cobs](https://github.com/micro-artwork/cobs)) or use Zephyr's native COBS module (`sys/cobs.h`).
- **Framed Channels**: For channels with native framing and integrity (UDP, BLE, TCP), raw 6-byte binary frames are transmitted directly without COBS overhead (`buildRawFrame` / `receiveRawDatagram`).

### 3.4 Buffer Isolation Modes (Double Buffering vs In-place)

Configured in `windrpc_config.h`:

```c
// 0: Double Buffer Mode (Separated RX/TX buffers. Recommended for full-duplex)
// 1: In-place Mode (Shared single buffer. Half-duplex only)
#define WINDRPC_USE_INPLACE_BUFFER 0
```

### 3.5 Core Version Handshake (`PingResponse`)

Invoking common `ping` (`0x0601`) returns both core framework version and user spec version:

```protobuf
message PingResponse {
    uint32 core_version_code = 1;  // Core framework version code (e.g. 10000)
    string core_version_name = 2;  // Core framework version string (e.g. "1.0.0")
    uint32 spec_version_code = 3;  // Spec firmware version code (e.g. 10000)
    string spec_version_name = 4;  // Spec firmware version string (e.g. "1.0.0")
}
```

### 3.6 Multi-Client & Multi-Channel Considerations

The WindRPC C server engine is a stateless, zero-heap framework primarily designed for 1:1 communication (single server to single client) in resource-constrained microcontroller (MCU) environments.

If you need to support multiple concurrent clients or multiple physical channels (e.g. concurrent UART + BLE, multiple UDP clients), developers must construct the following higher-layer routing mechanisms within their application layer:

1. **Message Queue-Based Sequential Processing**: Incoming packets from multiple channels should be queued into an RTOS message queue (e.g., FreeRTOS Queue, Zephyr `k_msgq`) or ring buffer, and processed sequentially by a single worker thread invoking `windrpc_handle(&txn)`.
2. **Client Routing & Outer Framing Layer**: Because the 6-byte raw binary header does not contain a client ID field, developers must implement an outer transport framing wrapper or manage a channel mapping layer in application code to route matching response frames back to the correct client.
3. **Double Buffer Mode Recommended**: Always configure `WINDRPC_USE_INPLACE_BUFFER 0` (Double Buffer Mode) to prevent RX/TX buffer corruption when handling concurrent channel streams.

---

> [!NOTE]
> **Why `syntax = "proto3"` instead of Protobuf Editions?**
>
> Protobuf Editions (e.g. `edition = "2023"`) is the modern successor to `proto2`/`proto3` syntax and is supported by the latest `protoc` releases. However, WindRPC relies on **[nanopb](https://github.com/nanopb/nanopb)** for C code generation on MCUs — and nanopb's generator plugin currently (as of 2026) **does not support Protobuf Editions**. Because nanopb cannot interpret edition-based feature flags, all generated `.proto` files use `syntax = "proto3"` until nanopb officially adds Editions support.

---


## 4. C Server Engine Integration

### 4.1 Server Handler Callbacks

Implement application logic in `windrpc_callbacks.c`:

```c
#include "windrpc.h"

int32_t windrpc_on_get_power_status(const rpc_types_Empty_t *req, rpc_power_manager_PowerStatus_t *res, void *context) {
    (void)req;
    (void)context;
    
    res->voltage_mv = 3300;
    res->is_charging = true;
    return 0; // Return 0 for success
}
```

### 4.2 Event Loop Binding

```c
#include "windrpc.h"

static uint8_t tx_buf[512];

void process_incoming_packet(uint8_t *data, size_t len) {
    struct windrpc_transaction txn = {
        .buffer = {
            .data = data,
            .size = len,
            .bytes_written = (uint16_t)len,
            .tx_data = tx_buf,
            .tx_size = sizeof(tx_buf)
        }
    };

    int32_t status = windrpc_handle(&txn);
    if (status == 0 && txn.buffer.bytes_written > 0) {
        transport_send(txn.buffer.tx_data, txn.buffer.bytes_written);
    }
}
```

> [!NOTE]
> **`windrpc_handle(&txn)` Return Value Semantics**
> Returning `0` from `windrpc_handle` signifies that a response packet (either a normal RPC response or a `0x0000` System Error response) was successfully generated into `tx_data` for transmission. A negative return value (`-1`) indicates a fatal framing or buffer size failure where no response packet could be produced. Application-level RPC error codes are stored in `txn.context.status_code`.

### 4.3 Build Rules & Concurrency

- `prj.conf` settings:
  ```ini
  CONFIG_NANOPB=y
  CONFIG_NANOPB_WITHOUT_64BIT=y
  CONFIG_COBS=y
  ```
- Task Stack: Allocate at least **2KB-4KB stack** for WindRPC worker threads.

## 5. Client SDK Integration (JS/TS & C#)

### 5.1 JavaScript / TypeScript SDK (Node.js & Electron)

#### 5.1.1 Generation

```bash
windrpc client -s user_spec.yml -o src/communication/windrpc --lang js
```

This produces a single self-contained file — `WindRpcClient.js` — with no external dependencies. All Protobuf encoding/decoding and COBS framing logic is inlined.

---

#### 5.1.2 Import & Instantiation

```javascript
// ES Module (Electron renderer / Node.js ESM)
import { WindRpcClient } from './windrpc/WindRpcClient.js';

const client = new WindRpcClient();
```

> **Note**: `WindRpcClient.js` is a standard ES Module (`export`). In Electron, ensure `nodeIntegration` or `contextBridge` is configured appropriately for your security model.

---

#### 5.1.3 Transport Binding

WindRPC is transport-agnostic. Bind `WindRpcClient` to any transport by connecting two directions:

**RX — Feeding received bytes into the client**

| Channel | Method | When to use |
| :--- | :--- | :--- |
| Serial (UART, USB-CDC) | `receiveBytes(chunk, onNotification)` | Byte stream with COBS `0x00` delimiters |
| UDP / BLE datagram | `receiveRawDatagram(bytes, onNotification)` | Already-framed, complete packets |

```javascript
// Serial / COBS stream (e.g. node-serialport)
serialPort.on('data', (chunk) => {
    client.receiveBytes(chunk, handleNotification);
});

// UDP datagram socket
udpSocket.on('message', (msg) => {
    client.receiveRawDatagram(msg, handleNotification);
});
```

**TX — Sending frames from the client**

| Channel | Builder | Output |
| :--- | :--- | :--- |
| Serial / COBS | `buildCobsFrame(rpcId, payload?)` | COBS-encoded bytes with `0x00` delimiter |
| UDP / raw | `buildRawFrame(rpcId, payload?)` | Plain 6-byte header + payload |

---

#### 5.1.4 Sending a Request-Response RPC

Use `sendRequest(rpcId, payloadBytes, sendFn, timeoutMs?)` to send a request and await the response as a `Promise`.

```javascript
import { decodePowerManagerPowerStatus, encodePowerManagerGetPowerStatusRequest }
    from './windrpc/WindRpcClient.js';

// RPC ID: service 8 (0x08), rpc 1 (0x01) -> 0x0801
const RPC_GET_POWER_STATUS = 0x0801;

async function readPowerStatus() {
    // 1. Encode request payload (Empty in this case -> empty Uint8Array)
    const reqPayload = encodePowerManagerGetPowerStatusRequest({});

    // 2. Send and await response
    const responseFrame = await client.sendRequest(
        RPC_GET_POWER_STATUS,
        reqPayload,
        (frame) => serialPort.write(frame), // sendFn: how to transmit the frame
        3000                                 // timeout (ms), default: 2000
    );

    // 3. Decode response payload
    const status = decodePowerManagerPowerStatus(responseFrame.payload);
    console.log(`Voltage: ${status.voltage_mv} mV, Charging: ${status.is_charging}`);
    return status;
}
```

> **Error Handling**: `sendRequest` rejects the Promise on timeout or if the server returns `RPC_ID 0x0000` (system error). Wrap in `try/catch`.

```javascript
try {
    const status = await readPowerStatus();
} catch (err) {
    console.error('RPC failed:', err.message);
}
```

#### 5.1.5 Receiving Notifications (Server Push)

Notifications are server-pushed asynchronous events sent after a client establishes a subscription by registering an event listener or sending a subscription RPC to the server. Incoming notification frames are dispatched to the subscribed `onNotification` callback passed to `receiveBytes` / `receiveRawDatagram`.

```javascript
import { decodePowerManagerPowerStatus } from './windrpc/WindRpcClient.js';

const RPC_CHARGING_ALERT = 0x0882; // service 8 (0x08), event rpc 2 with MSB set (0x82)

function handleNotification(notification) {
    const { rpcId, payload } = notification;

    if (rpcId === RPC_CHARGING_ALERT) {
        const alert = decodePowerManagerPowerStatus(payload);
        console.log(`[ALERT] Charging state changed: ${alert.is_charging}`);
    }
}

serialPort.on('data', (chunk) => {
    client.receiveBytes(chunk, handleNotification);
});
```

> **Notification RPC ID rule**: Notification event IDs have bit 7 of the low byte set (`rpc_id | 0x80`). For service 8, rpc id 2 → `(0x08 << 8) | (0x02 | 0x80)` = `0x0882`.

---

#### 5.1.6 Ping & Version Handshake

Send a `ping` (RPC ID `0x0601`) to verify connectivity and retrieve core/spec version information. The response is automatically decoded and logged.

```javascript
// The client auto-decodes and logs PingResponse when 0x0601 is received.
// Manually send a ping frame:
const pingFrame = client.buildCobsFrame(0x0601);
serialPort.write(pingFrame);

// Alternatively use sendRequest to await the PingResponse explicitly:
const pingResp = await client.sendRequest(
    0x0601,
    new Uint8Array(0),
    (frame) => serialPort.write(frame)
);
// pingResp.payload contains the raw PingResponse protobuf bytes
```

---

#### 5.1.7 Accumulator Reset

If the serial connection is reset or you detect a corrupt stream, call `resetAccumulator()` to clear internal byte buffer state and reject all pending requests:

```javascript
serialPort.on('close', () => {
    client.resetAccumulator();
});
```

---

### 5.2 C# WinForms / .NET SDK

#### 5.2.1 Generation

```bash
windrpc client -s user_spec.yml -o Communication/WindRpc --lang csharp
```

This produces:
- `WindRpcClient.cs` — Transport-agnostic RPC client (`RpcHandler`)
- `Generated/*.cs` — Protobuf data class files compiled from `.proto` schemas

> **Prerequisite**: `protoc` must be available on `PATH` (e.g. via Chocolatey: `choco install protoc`). The generator automatically invokes `protoc` to compile `.proto` → `.cs`.

---

#### 5.2.2 Project Setup

Add the generated files to your `.csproj` and install the required NuGet package:

```bash
dotnet add package Google.Protobuf
```

Ensure the generated `Generated/*.cs` files are included in your project (they will be auto-discovered if inside the project directory).

---

#### 5.2.3 Instantiation & Transport Binding

`RpcHandler` requires a `Func<byte[], Task>` delegate for sending frames, and exposes a `ReceiveBytes(byte[])` method for feeding incoming data.

```csharp
using HilightBox.Communication.WindRpc;

// Create the handler with a send delegate
var rpcHandler = new RpcHandler(async (frame) =>
{
    await serialPort.BaseStream.WriteAsync(frame, 0, frame.Length);
});

// Feed received bytes into the handler (call from your serial data event)
serialPort.DataReceived += (s, e) =>
{
    var buf = new byte[serialPort.BytesToRead];
    serialPort.Read(buf, 0, buf.Length);
    rpcHandler.ReceiveBytes(buf);
};
```

---

#### 5.2.4 Sending a Request-Response RPC

```csharp
using Google.Protobuf;
using MyProject.Windrpc.Service.PowerManager;

public class PowerService
{
    private readonly RpcHandler _rpcHandler;

    public PowerService(RpcHandler handler) => _rpcHandler = handler;

    public async Task<PowerStatus> GetPowerStatusAsync()
    {
        // RPC ID: service 8 (0x08), rpc 1 (0x01) -> 0x0801
        const int RpcId = 0x0801;

        // Send request with an Empty payload
        var response = await _rpcHandler.SendRequestAsync(
            RpcId,
            ByteString.Empty.ToByteArray(),
            timeoutMs: 3000);

        // Parse response payload into a Protobuf message
        return PowerStatus.Parser.ParseFrom(response.Payload);
    }
}
```

---

#### 5.2.5 Handling Notifications (Server Push)

Register an `OnNotification` callback on `RpcHandler` to receive server-pushed events:

```csharp
using MyProject.Windrpc.Service.PowerManager;

// RPC ID: service 8 (0x08), event rpc 2 (0x02 | 0x80) -> 0x0882
const int RpcChargingAlert = 0x0882;

rpcHandler.OnNotification += (notification) =>
{
    if (notification.RpcId == RpcChargingAlert)
    {
        var alert = PowerStatus.Parser.ParseFrom(notification.Payload);
        Console.WriteLine($"[ALERT] Charging: {alert.IsCharging}, Voltage: {alert.VoltageMv} mV");
    }
};
```

---

#### 5.2.6 Ping & Version Handshake

```csharp
using MyProject.Windrpc.Core;  // PingResponse is in the core package

public async Task PingAsync()
{
    var response = await _rpcHandler.SendRequestAsync(
        0x0601,
        Array.Empty<byte>());

    var pingResponse = PingResponse.Parser.ParseFrom(response.Payload);
    Console.WriteLine($"Core: {pingResponse.CoreVersionName} ({pingResponse.CoreVersionCode})");
    Console.WriteLine($"Spec: {pingResponse.SpecVersionName} ({pingResponse.SpecVersionCode})");
}
```

---

#### 5.2.7 Timeout & Error Handling

`SendRequestAsync` throws a `TimeoutException` if no response is received within the configured timeout, and a `RpcException` if the server returns an error status (RPC ID `0x0000`).

```csharp
try
{
    var status = await _powerService.GetPowerStatusAsync();
}
catch (TimeoutException)
{
    Console.Error.WriteLine("RPC timed out.");
}
catch (RpcException ex)
{
    Console.Error.WriteLine($"RPC error: {ex.StatusCode} - {ex.Message}");
}
```

---

### 5.3 Python Client SDK (`WindRpcClient.py`)

#### 5.3.1 Code Generation

```bash
windrpc client -s user_spec.yml -o client/python -l python
```

Generated Output:
- `WindRpcClient.py` — Single-file Python Client SDK (`WindRpcClient` class, COBS encoding/decoding, 6-byte raw header packing, `asyncio` async API)
- `Generated/*_pb2.py` — Compiled Protobuf data classes from `.proto` schemas
- `Protos/*.proto` — Reference Protobuf schema and `.options` files

#### 5.3.2 Reception & Transport Binding (Datagram / Byte Stream)

```python
import asyncio
from WindRpcClient import WindRpcClient, RPC_POWER_MANAGER_GET_POWER_STATUS, RPC_POWER_MANAGER_CHARGING_ALERT
from my_package.windrpc.service import power_manager_pb2

client = WindRpcClient()

# Datagram Channels (UDP / BLE):
def on_udp_rx(data):
    client.receive_raw_datagram(data, on_notification=handle_notification)

# Byte Stream Channels (UART / COBS):
def on_uart_rx(chunk):
    client.receive_bytes(chunk, on_notification=handle_notification)
```

#### 5.3.3 Async Request-Response Invocation (`asyncio`)

```python
async def fetch_power_status(transport_send_fn):
    response_frame = await client.send_request_async(
        RPC_POWER_MANAGER_GET_POWER_STATUS,
        b"", # Request payload
        transport_send_fn,
        timeout_ms=3000
    )
    status = power_manager_pb2.PowerStatus()
    status.ParseFromString(response_frame.payload)
    return status
```

#### 5.3.4 Handling Notifications (Server Push)

```python
def handle_notification(frame):
    if frame.rpc_id == RPC_POWER_MANAGER_CHARGING_ALERT:
        alert = power_manager_pb2.PowerStatus()
        alert.ParseFromString(frame.payload)
        print(f"[ALERT] Charging: {alert.is_charging}, Voltage: {alert.voltage_mv} mV")
```

---

## 6. CLI Command Reference

```bash
# 1. Generate standalone .proto and .options files
windrpc proto -s user_spec.yml -o protos

# 2. Generate C server engine (Includes .proto generation)
windrpc server -s user_spec.yml -o server

# 3. Generate JS/TS client SDK (Includes .proto generation)
windrpc client -s user_spec.yml -o client/js -l js

# 4. Generate C# client SDK (Includes .proto generation)
windrpc client -s user_spec.yml -o client/csharp -l csharp

# 5. Generate Python client SDK (Includes .proto generation)
windrpc client -s user_spec.yml -o client/python -l python
```

