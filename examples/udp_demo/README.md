# WindRPC UDP Integrated End-to-End Demo

This example demonstrates how to use WindRPC over an un-framed, zero-overhead **UDP Datagram channel**. It features a **C UDP Server** (simulating an embedded MCU firmware) alongside **Node.js (JS)** and **Python** client applications.

---

## 📁 Directory Structure & File Classification

To make learning easy, files are clearly classified into **User-Written** vs **Auto-Generated**:

```text
examples/udp_demo/
├── device_spec.yml           [USER-WRITTEN]    RPC Descriptor defining services & messages
├── generate.py               [AUTOMATION]      One-stop script invoking windrpc_gen.py
├── README.md                 [DOCUMENTATION]   This guide
├── c_server/
│   ├── CMakeLists.txt        [USER-WRITTEN]    CMake build configuration
│   ├── main.c                [USER-WRITTEN]    UDP Socket binding & windrpc_handle() event loop
│   ├── windrpc_callbacks.c   [USER-WRITTEN]    Business logic callbacks (windrpc_on_get_power_status, etc.)
│   └── generated/            [AUTO-GENERATED]  WindRPC C Dispatcher & Nanopb schemas
├── js_client/
│   ├── app.mjs               [USER-WRITTEN]    Node.js Client app using generated WindRpcClient.js
│   └── generated/            [AUTO-GENERATED]  WindRpcClient.js SDK
└── py_client/
    ├── app.py                [USER-WRITTEN]    Python Client app using generated WindRpcClient.py
    └── generated/            [AUTO-GENERATED]  WindRpcClient.py SDK & *_pb2.py Data Classes
```

---

## ⚡ One-Touch Automated Generation & Verification

Run `run_demo.py`. It automatically generates code, compiles the C UDP server, launches the background server, executes JS and Python clients, and verifies output:

```bash
python run_demo.py
```

---

## 🚀 Manual Step-by-Step Guide

### Step 1: Generate Code for All Languages

Run `generate.py` to auto-generate C Server code, JS Client SDK, and Python Client SDK from `device_spec.yml`:

```bash
python generate.py
```

---

### Step 2: Build & Start C UDP Server

```bash
cd c_server
cmake -B build -S .
cmake --build build
```

Run the server executable:

```bash
# Windows
.\build\udp_server.exe

# Linux / macOS
./build/udp_server
```

---

### Step 3: Run Node.js Client (JavaScript)

In a separate terminal:

```bash
cd js_client
node app.mjs
```

---

### Step 4: Run Python Client (Python)

In a separate terminal:

```bash
cd py_client
python app.py
```

---

## 💡 How it Works

### 1. User Spec Definition (`device_spec.yml`)
Services, messages, and RPC types are defined in YAML. WindRPC generates matching C server dispatchers and client SDKs.

### 2. C Server Callback Implementation (`windrpc_callbacks.c`)
Developers implement simple business callbacks without worrying about manual binary packet parsing:

```c
int32_t windrpc_on_get_power_status(const void *req, rpc_power_manager_PowerStatus_t *res, void *context) {
    res->voltage_mv = 3300;
    res->current_ma = 450;
    res->is_charging = true;
    return 0; // 0 = SUCCESS
}
```

### 3. Client RPC Calls (JS & Python)
Clients send RPC requests and handle server push notifications:

```javascript
// Node.js
const status = await client.sendRequest(RPC_POWER_MANAGER_GET_POWER_STATUS, new Uint8Array(0), sendFn);
```

```python
# Python
status = await client.send_request_async(RPC_POWER_MANAGER_GET_POWER_STATUS, b"", send_fn)
```
