# WindRPC LLM Agent Guidelines

This document provides instructions and guidelines for AI Coding Agents (Gemini Antigravity, Cursor, Windsurf, Claude, Copilot, etc.) working with or integrating **WindRPC**.

---

## 1. Executive Summary for AI Agents

**WindRPC** is a zero-heap, static-memory RPC framework designed for microcontroller firmware (C MCU) and client applications (Electron JS/TS & C# WinForms).

### Key Architectural Concepts
1. **RPC Descriptor (`user_spec.yml`)**: All RPC interfaces, data messages, and enums are defined in a YAML specification file. Code for C servers, JS clients, and C# clients is **automatically generated** from this specification.
2. **6-Byte Binary Header**: Communication uses a fixed 6-byte raw binary header (Little-Endian) directly preceding Protobuf payload bytes.
   - Header format: `[RPC_ID (2B)][SEQ_ID (2B)][PAYLOAD_LEN (2B)]`
   - `RPC_ID` = `(service_id << 8) | rpc_id`
3. **Transport Independence**: Supports COBS framing for serial byte streams (UART, USB-CDC) and raw datagram framing for packet channels (UDP, BLE, TCP).

---

## 2. Mandatory Rules for AI Agents

> [!IMPORTANT]
> **Rule 1: Never Manually Edit Generated Files**
> Do NOT directly edit files in output directories (e.g. `generated_flat`, `WindRpcClient.js`, `Generated/*.cs`, `.proto` files). Always modify the YAML specification (`user_spec.yml` or `<project>_spec.yml`) and re-run `windrpc_gen.py`.

> [!IMPORTANT]
> **Rule 2: Respect Reserved Range & Naming Rules**
> - **Service IDs 1 through 6 are reserved** for WindRPC core services (`common`, etc.). User services **MUST use IDs 7 to 255**.
> - **RPC ID `0x0000`** is reserved for System Error responses.
> - **RPC ID `0x0601`** is reserved for Core Ping/Version Handshake.
> - Validator enforces strict naming rules:
>   - `package`, `service`, `rpc`, `field`: `snake_case`
>   - `message`, `enum`: `PascalCase`
>   - `enum member`: `UPPER_SNAKE_CASE`

> [!WARNING]
> **Rule 3: Maintain `syntax = "proto3"`**
> Do NOT change `.proto` generator syntax to `edition = "2023"`. The C MCU side relies on **Nanopb**, which does not yet support Protobuf Editions.

> [!CAUTION]
> **Rule 4: Zero-Heap Allocation in C Callbacks**
> When writing MCU callback handlers in C (`windrpc_callbacks.c`), NEVER use dynamic memory allocation (`malloc`, `calloc`, `free`). Nanopb structures use static allocation based on `nanopb:` constraints in the YAML spec.

---

## 3. Code Generation Workflow

Whenever you add or modify RPCs, messages, or services in YAML spec:

### 3.1 CLI Command Cheat Sheet

```bash
# 1. Generate .proto and Nanopb .options files independently
python windrpc/windrpc_gen.py proto -s user_spec.yml -o protos

# 2. Generate C Server Engine (Includes .proto generation)
python windrpc/windrpc_gen.py server -s user_spec.yml -o server/windrpc

# 3. Generate Electron / Node.js Client SDK (Includes .proto generation)
python windrpc/windrpc_gen.py client -s user_spec.yml -o client/js --lang js

# 4. Generate C# WinForms / .NET Client SDK (Includes .proto generation)
python windrpc/windrpc_gen.py client -s user_spec.yml -o client/csharp --lang csharp

# 5. Generate Python Client SDK (Includes .proto generation)
python windrpc/windrpc_gen.py client -s user_spec.yml -o client/python --lang python
```

---

## 4. Integration Templates for Agents

### 4.1 C Server Callback Implementation (`windrpc_callbacks.c`)

When implementing C server handlers:

```c
#include "windrpc.h"

// REQUEST_RESPONSE Handler Signature:
// int32_t windrpc_on_<service_name>_<rpc_name>(const rpc_<svc>_<Req>_t *req, rpc_<svc>_<Res>_t *res, void *context)
int32_t windrpc_on_power_manager_get_power_status(const rpc_types_Empty_t *req, rpc_power_manager_PowerStatus_t *res, void *context) {
    (void)req;
    (void)context;

    res->voltage_mv = 3300;
    res->is_charging = true;
    return 0; // Return 0 for success
}

// NOTIFICATION Event Push Helper:
// int32_t windrpc_notify_<rpc_name>(const rpc_<svc>_<Event>_t *data, struct windrpc_transaction *txn)
```

### 4.2 C Server Event Loop Binding

```c
#include "windrpc.h"

static uint8_t tx_buf[512];

void process_incoming_packet(uint8_t *rx_data, size_t rx_len) {
    struct windrpc_transaction txn = {
        .buffer = {
            .data = rx_data,
            .size = rx_len,
            .bytes_written = (uint16_t)rx_len,
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

### 4.3 Electron JS Client Integration (`WindRpcClient.js`)

```javascript
import { WindRpcClient, decodePowerManagerPowerStatus } from './windrpc/WindRpcClient.js';

const client = new WindRpcClient();

// 1. RX Binding for Serial/COBS stream
serialPort.on('data', (chunk) => {
    client.receiveBytes(chunk, (notification) => {
        // Notification Handler
        if (notification.rpcId === 0x0882) { // (service 8, event rpc 2)
            const alert = decodePowerManagerPowerStatus(notification.payload);
            console.log('Server Push Alert:', alert);
        }
    });
});

// 2. Request-Response RPC Call
async function fetchPowerStatus() {
    const responseFrame = await client.sendRequest(
        0x0801, // (service 8, rpc 1)
        new Uint8Array(0),
        (frame) => serialPort.write(frame),
        3000 // Timeout ms
    );
    return decodePowerManagerPowerStatus(responseFrame.payload);
}
```

### 4.4 C# WinForms Client Integration (`WindRpcClient.cs`)

```csharp
using HilightBox.Communication.WindRpc;
using MyProject.Windrpc.Service.PowerManager;

var rpcHandler = new RpcHandler(async (frame) => {
    await serialPort.BaseStream.WriteAsync(frame, 0, frame.Length);
});

serialPort.DataReceived += (s, e) => {
    var buf = new byte[serialPort.BytesToRead];
    serialPort.Read(buf, 0, buf.Length);
    rpcHandler.ReceiveBytes(buf);
};

// Send Request
var response = await rpcHandler.SendRequestAsync(0x0801, Array.Empty<byte>());
var status = PowerStatus.Parser.ParseFrom(response.Payload);
```

### 4.5 Python Client Integration (`WindRpcClient.py`)

```python
import asyncio
from WindRpcClient import WindRpcClient, RPC_POWER_MANAGER_GET_POWER_STATUS
from my_package.windrpc.service import power_manager_pb2

client = WindRpcClient()

# 1. RX Binding for Datagram (UDP / BLE) or Byte Stream (UART)
def on_raw_rx(data):
    client.receive_raw_datagram(data, on_notification=lambda frame: print("Push:", frame))

# 2. Async Request-Response RPC Call
async function fetch_status(transport_send_fn):
    response_frame = await client.send_request_async(
        RPC_POWER_MANAGER_GET_POWER_STATUS,
        b"",
        transport_send_fn,
        timeout_ms=3000
    )
    status = power_manager_pb2.PowerStatus()
    status.ParseFromString(response_frame.payload)
    return status
```

---

## 5. Verification & Testing Procedure

After generating code or modifying specifications, AI Agents MUST verify correctness by running the integrated test suite:

```bash
python run_tests.py
```

This runs:
1. Python Validator Unit Tests
2. Auto-generation of Flat Proto & C Server Code
3. Host C Compilation & Test Execution (Double Buffer & In-place modes)
4. JS Client SDK Generation & Node.js Unit Tests
5. C# Client SDK Generation & `protoc` Compilation Check
6. Python Client SDK Generation & Execution Unit Tests

Ensure `ALL WINDRPC INTEGRATED TESTS PASSED SUCCESSFULLY!` is logged before concluding tasks.
