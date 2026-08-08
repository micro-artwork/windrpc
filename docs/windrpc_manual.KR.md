# WindRPC 레퍼런스 및 통합 매뉴얼 (WindRPC Reference Manual)

본 문서는 WindRPC 프레임워크의 사양서 작성 가이드, 이진 헤더 프레임 메커니즘, C 서버 엔진 구현, 클라이언트 SDK 연동 및 동시성 가이드를 하나로 통합한 종합 레퍼런스 문서입니다.

---

## 목차 (Table of Contents)

1. [개요 및 특징 (Overview)](#1-개요-및-특징-overview)
2. [사양서 작성 가이드 (`user_spec.yml`)](#2-사양서-작성-가이드-user_specyml)
   - [2.1 파일 구성 및 기본 구조](#21-파일-구성-및-기본-구조)
   - [2.2 명명 규칙 및 스타일 가이드 (Naming Rules)](#22-명명-규칙-및-스타일-가이드-naming-rules)
   - [2.3 서비스 ID 및 RPC 유형](#23-서비스-id-및-rpc-유형)
   - [2.4 정적 메모리 설계 (NanoPB 옵션)](#24-정적-메모리-설계-nanopb-옵션)
   - [2.5 user_spec.yml 작성 템플릿](#25-user_specyml-작성-템플릿)
3. [아키텍처 및 이진 프레임 메커니즘](#3-아키텍처-및-이진-프레임-메커니즘)
   - [3.1 6바이트 이진 헤더 프레임 규격](#31-6바이트-이진-헤더-프레임-규격)
   - [3.2 16비트 Combined RPC ID 규칙](#32-16비트-combined-rpc-id-규칙)
   - [3.3 전송 레이어 역할 범위 및 COBS 유틸리티 제공](#33-전송-레이어-역할-범위-및-cobs-유틸리티-제공)
   - [3.4 수신/송출 버퍼 분리 옵션 (Double Buffering vs In-place)](#34-수신송출-버퍼-분리-옵션-double-buffering-vs-in-place)
   - [3.5 코어 버저닝 핸드셰이크 (`PingResponse`)](#35-코어-버저닝-핸드셰이크-pingresponse)
   - [3.6 멀티 클라이언트 및 멀티 채널 응용 안내](#36-멀티-클라이언트-및-멀티-채널-응용-안내-multi-client--multi-channel-considerations)
4. [C 서버 엔진 연동](#4-c-서버-엔진-연동)
   - [4.1 서버 콜백 구현](#41-서버-콜백-구현)
   - [4.2 서버 이벤트 루프 바인딩](#42-서버-이벤트-루프-바인딩)
   - [4.3 빌드 및 멀티스레드 주의사항](#43-빌드-및-멀티스레드-주의사항)
5. [클라이언트 SDK 연동 (JS/TS & C#)](#5-클라이언트-sdk-연동-jsts--c)
   - [5.1 JavaScript / TypeScript SDK (Node.js & Electron)](#51-javascript--typescript-sdk-nodejs--electron)
   - [5.2 C# WinForms / .NET SDK](#52-c-winforms--net-sdk)
6. [CLI 명령 레퍼런스](#6-cli-명령-레퍼런스)

---

## 1. 개요 및 특징 (Overview)

WindRPC는 마이크로프로세서(MCU) 및 이기종 클라이언트(Electron, C# WinForms 등) 환경에서 동작하도록 설계된 초경량 원격 프로시저 호출(RPC) 프레임워크입니다.

- **Zero-Heap Static Memory**: 동적 메모리 할당(`malloc`/`free`) 없는 100% 정적 메모리 운용으로 장기 구동 안정성 보장.
- **6바이트 이진 헤더 프레임**: Outer Protobuf 감싸기 구조 없이 6바이트 이진 헤더 + Protobuf 페이로드 직결 구조로 $O(1)$ Direct Lookup 디스패칭 수행.
- **단일 YAML 명세 기반 코드 자동 생성**: `user_spec.yml` 파일 하나로 Protobuf 스키마, Nanopb C 서버 코드, JS/TS 및 C# 클라이언트 SDK 원스톱 자동 생성.
- **독립적 전송 레이어**: COBS 프레이밍 및 외부 CRC 무결성 검증을 사용자의 필요에 따라 선택 연동 가능.

---

## 2. 사양서 작성 가이드 (`user_spec.yml`)

### 2.1 파일 구성 및 기본 구조

`user_spec.yml` 파일은 프로젝트 네임스페이스(`package`), 명세서 버전 정보(`info`), 그리고 사용자 서비스/메시지/RPC 정의(`services`) 영역으로 구성됩니다.

```yaml
package: my_project

info:
  title: "My Control Specification"
  version: "1.0.0"
  version_code: 10000
  version_name: "1.0.0"

services:
  # 서비스 및 RPC 정의
```

> **파일명 유연성**: `user_spec.yml`은 기본 예시입니다. `-s <명세서_파일명>.yml` 옵션을 통해 자유롭게 지정할 수 있습니다.

### 2.2 명명 규칙 및 스타일 가이드 (Naming Rules)

명세서 검증기(`spec_validator.py`)는 다음 규칙(`^[a-zA-Z_][a-zA-Z0-9_]*$`)을 엄격히 검사합니다:

| 대상 | 스타일 | 적용 정규식 | 올바른 예시 | 잘못된 예시 |
| :--- | :--- | :--- | :--- | :--- |
| **package** | `snake_case` | `^[a-z][a-z0-9_]*$` | `my_project` | `my-project`, `MyProject` |
| **Service** | `snake_case` | `^[a-z][a-z0-9_]*$` | `power`, `led_control` | `PowerService`, `led-control` |
| **Message** | `PascalCase` | `^[A-Z][a-zA-Z0-9]*$` | `PowerInfo`, `PixelData` | `power_info`, `pixelData` |
| **Enum** | `PascalCase` | `^[A-Z][a-zA-Z0-9]*$` | `LedColor`, `DeviceStatus` | `led_color`, `status` |
| **Enum Member** | `UPPER_SNAKE_CASE` | `^[A-Z0-9_]+$` | `COLOR_RED`, `NONE` | `ColorRed`, `color_red` |
| **RPC Method** | `snake_case` | `^[a-z0-9_]+$` | `read_power_info` | `ReadPower`, `read-power` |
| **Field** | `snake_case` | `^[a-z0-9_]+$` | `voltage_mv` | `voltageMv`, `Voltage_Mv` |

### 2.3 서비스 ID 및 RPC 유형

- **서비스 ID 예약 구간**: **Service ID 1번부터 6번까지는 WindRPC 코어 예약 구간**입니다. 사용자 서비스는 **7~255번** 범위 정수를 지정해야 합니다.
- **RPC 유형 (`type`)**:
  1. `REQUEST_ONLY`: 단방향 요청 (서버 응답 없음). `request` 지정 필요.
  2. `REQUEST_RESPONSE`: 양방향 표준 RPC. `request` 및 `response` 지정 필요.
  3. `NOTIFICATION`: 서버 푸시 비동기 이벤트. `event` 지정 필요.

### 2.4 정적 메모리 설계 (NanoPB 옵션)

메시지 필드에 `nanopb:` 옵션을 지정하여 고정 메모리 크기를 제한합니다 (미지정 시 기본값: `string`/`bytes` 64바이트, `repeated` 16개):

```yaml
fields:
  - number: 1
    name: colors
    type: PixelColor
    property: repeated
    nanopb: { max_count: 64 } # 배열 최대 개수 64개 정적 제한
```

### 2.5 user_spec.yml 작성 템플릿

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

## 3. 아키텍처 및 이진 프레임 메커니즘

### 3.1 6바이트 이진 헤더 프레임 규격

WindRPC는 고정 6바이트 이진 헤더(Little-Endian)와 Protobuf 페이로드 직결 구조를 다룹니다:

```text
+-------------------+-------------------+-------------------+--------------------------------+
|  RPC_ID (2 Bytes) |  SEQ_ID (2 Bytes) | PAYLOAD_LEN (2B)  |   PAYLOAD (Protobuf 바이너리)  |
+-------------------+-------------------+-------------------+--------------------------------+
|     0x03 0x07     |     0x01 0x00     |    0x00 0x02      | [NanoPB로 인코딩된 데이터 바이트] |
+-------------------+-------------------+-------------------+--------------------------------+
  |<---------------- 6바이트 고정 이진 헤더 (Raw Binary, Little-Endian) ------------->|
```

- `RPC_ID` (2B, Little-Endian): `(service_id << 8) | rpc_id`
- `SEQ_ID` (2B, Little-Endian): 시퀀스/트랜잭션 식별자 (`uint16_t`)
- `PAYLOAD_LEN` (2B, Little-Endian): Protobuf 페이로드 바이트 길이를 지칭하는 16비트 정수

### 3.2 16비트 Combined RPC ID 규칙

$$\text{combined\_id} = (\text{service\_id} \ll 8) \mid \text{rpc\_id}$$

- Service ID 1~6: WindRPC 코어 예약 구간 (`common` 등)
- Service ID 7~255: 사용자 정의 비즈니스 서비스 구간
- RPC ID 1~255: 서비스 내부 개별 메서드 ID
- 예약된 Combined RPC ID:
  - `0x0000`: 시스템 오류 응답 (전체 서비스 공통 예약)
  - `0x0601`: 코어 Ping / 버전 핸드셰이크 (항상 내장 제공)

### 3.3 전송 레이어 역할 범위 및 COBS 유틸리티 제공

WindRPC는 마이크로컨트롤러 환경의 복잡도를 최소화하기 위해 패킷 프레이밍 및 데이터 무결성 검증(CRC 등)을 전송 채널(Data Link)을 담당하는 사용자 애플리케이션의 역할로 정의합니다:

- **사용자 영역의 데이터 링크 구현**: 복잡한 데이터 링크 레이어 프로토콜 및 CRC/Checksum 계산 로직은 WindRPC 코어에 포함되지 않습니다. RS-485 등 노이즈 채널 필요 시 개발자가 전송 래퍼(Wrapper) 레이어에서 CRC16/CRC32를 직접 덧붙여 구현합니다.
- **클라이언트 SDK COBS 내장**: 자동 생성되는 클라이언트 SDK(JS/TS, C#, Python)에는 연속 시리얼 스트림(UART, USB-CDC)의 `0x00` 구분자 처리용 COBS 인코딩/디코딩 유틸리티가 기본 포함되어 있습니다 (`buildCobsFrame` / `receiveBytes`).
- **C MCU 서버 측 COBS 연동**: C MCU 서버 엔진(`windrpc.c`) 자체에는 COBS 로직이 내장되어 있지 않으나, Zephyr RTOS 용으로 구현된 C COBS 라이브러리([micro-artwork/cobs](https://github.com/micro-artwork/cobs)) 로직을 참고하거나 Zephyr 내장 모듈(`sys/cobs.h`)을 연동할 수 있습니다.
- **프레임 단위 채널**: 전송 채널 자체에서 프레임 경계와 무결성이 보장되는 채널(UDP Datagram, BLE, TCP)에서는 COBS 오버헤드 없이 6바이트 이진 헤더 패킷 그대로 빠르게 전송합니다 (`buildRawFrame` / `receiveRawDatagram`).

### 3.4 수신/송출 버퍼 분리 옵션 (Double Buffering vs In-place)

`windrpc_config.h`에서 설정:

```c
// 0: Double Buffer 모드 (RX/TX 버퍼 분리. 전이중/Full-duplex 권장)
// 1: In-place 모드 (단일 버퍼 공유. 반이중/Half-duplex 전용)
#define WINDRPC_USE_INPLACE_BUFFER 0
```

### 3.5 코어 버저닝 핸드셰이크 (`PingResponse`)

공통 `ping` (`0x0601`) 호출 시 프레임워크 코어 버전 및 사용자 스펙 버전을 함께 반환합니다:

```protobuf
message PingResponse {
    uint32 core_version_code = 1;  // 코어 프레임워크 버전 코드 (예: 10000)
    string core_version_name = 2;  // 코어 프레임워크 버전 문자열 (예: "1.0.0")
    uint32 spec_version_code = 3;  // 사용자 스펙 버전 코드 (예: 10000)
    string spec_version_name = 4;  // 사용자 스펙 버전 문자열 (예: "1.0.0")
}
```

### 3.6 멀티 클라이언트 및 멀티 채널 응용 안내 (Multi-Client & Multi-Channel Considerations)

WindRPC C 서버 엔진은 자원이 제한된 마이크로컨트롤러(MCU) 환경의 1:1 통신(단일 서버 - 단일 클라이언트)을 주요 목표로 설계된 무상태(Stateless), Zero-Heap 프레임워크입니다.

만약 멀티 클라이언트나 복수 전송 채널(예: 동시 UART + BLE, 복수 UDP 등) 환경에서 확장하여 사용하고자 할 경우, 프레임워크 차원이 아닌 사용자 애플리케이션 상위 레이어에서 다음과 같은 수발신 구조를 직접 구축해야 합니다:

1. **메시지 큐 기반 순차 처리 (Message Queue Processing)**: 다양한 채널에서 동시에 들어오는 수신 패킷을 RTOS 메시지 큐(FreeRTOS `Queue`, Zephyr `k_msgq` 등)나 링 버퍼에 격리/큐잉한 후, 단일 작업(Task/Thread)에서 `windrpc_handle(&txn)`을 순차적으로 호출하도록 구성해야 합니다.
2. **클라이언트 식별 및 상위 라우팅 레이어 구축 (Client Routing Layer)**: WindRPC 6바이트 이진 헤더는 클라이언트 ID를 별도로 포함하지 않으므로, 요청 클라이언트를 구분하기 위해서는 사용자 상위 채널 프레임(예: 외각 채널 헤더 추가)을 두거나, 사용자 코드에서 요청 채널과 응답 채널을 매핑하는 라우팅 메커니즘을 구축해야 합니다.
3. **Double Buffer 모드 적용**: 복수 채널 처리 시 동시 수발신 프레임 충돌을 방지하기 위해 `WINDRPC_USE_INPLACE_BUFFER 0` (Double Buffer 모드) 설정을 권장합니다.

---

> [!NOTE]
> **왜 Protobuf Editions 대신 `syntax = "proto3"`를 사용하나요?**
>
> Protobuf Editions (예: `edition = "2023"`)는 Protobuf의 최신 사양으로 최신 `protoc`에서 지원됩니다. 그러나 WindRPC의 MCU(C 서버) 코드 생성기는 **[nanopb](https://github.com/nanopb/nanopb)**를 사용하는데, nanopb의 생성기 플러그인은 현재(2026년 기준) **Protobuf Editions를 공식 지원하지 않습니다**. nanopb가 edition 기반 기능 플래그를 해석할 수 없으므로, nanopb 공식 지원이 추가될 때까지 생성되는 모든 `.proto` 파일은 `syntax = "proto3"`를 사용합니다.

---

## 4. C 서버 엔진 연동

### 4.1 서버 콜백 구현

`windrpc_callbacks.c`에 비즈니스 로직 구현:

```c
#include "windrpc.h"

int32_t windrpc_on_get_power_status(const rpc_types_Empty_t *req, rpc_power_manager_PowerStatus_t *res, void *context) {
    (void)req;
    (void)context;
    
    res->voltage_mv = 3300;
    res->is_charging = true;
    return 0; // 0 반환 시 성공
}
```

### 4.2 서버 이벤트 루프 바인딩

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

### 4.3 빌드 및 멀티스레드 주의사항

- `prj.conf` 설정:
  ```ini
  CONFIG_NANOPB=y
  CONFIG_NANOPB_WITHOUT_64BIT=y
  CONFIG_COBS=y
  ```
- 스레드 스택 메모리: WindRPC 트랜잭션 처리 워커 스레드에는 최소 **2KB~4KB 스택** 할당을 권장합니다.

---

## 5. 클라이언트 SDK 연동 (JS/TS & C#)

### 5.1 JavaScript / TypeScript SDK (Node.js & Electron)

#### 5.1.1 생성

```bash
windrpc client -s user_spec.yml -o src/communication/windrpc --lang js
```

`WindRpcClient.js` 단일 파일이 생성됩니다. 외부 의존성이 없으며 Protobuf 인코딩/디코딩과 COBS 프레이밍 로직이 모두 인라인으로 포함됩니다.

---

#### 5.1.2 Import & 인스턴스 생성

```javascript
// ES Module (Electron renderer / Node.js ESM)
import { WindRpcClient } from './windrpc/WindRpcClient.js';

const client = new WindRpcClient();
```

> **참고**: `WindRpcClient.js`는 표준 ES Module(`export`)입니다. Electron에서는 보안 모델에 따라 `nodeIntegration` 또는 `contextBridge` 설정을 적절히 적용하세요.

---

#### 5.1.3 트랜스포트 바인딩

WindRPC는 트랜스포트에 독립적입니다. 수신(RX)과 송신(TX) 두 방향을 연결하여 사용합니다.

**RX — 수신 바이트를 클라이언트에 주입**

| 채널 | 메서드 | 사용 시점 |
| :--- | :--- | :--- |
| 시리얼 (UART, USB-CDC) | `receiveBytes(chunk, onNotification)` | COBS `0x00` 구분자 기반 바이트 스트림 |
| UDP / BLE 데이터그램 | `receiveRawDatagram(bytes, onNotification)` | 이미 완전한 패킷 단위로 수신되는 채널 |

```javascript
// 시리얼 / COBS 스트림 (예: node-serialport)
serialPort.on('data', (chunk) => {
    client.receiveBytes(chunk, handleNotification);
});

// UDP 데이터그램 소켓
udpSocket.on('message', (msg) => {
    client.receiveRawDatagram(msg, handleNotification);
});
```

**TX — 송신 프레임 빌드**

| 채널 | 빌더 | 출력 |
| :--- | :--- | :--- |
| 시리얼 / COBS | `buildCobsFrame(rpcId, payload?)` | COBS 인코딩된 바이트 + `0x00` 구분자 |
| UDP / 원시 | `buildRawFrame(rpcId, payload?)` | 6바이트 헤더 + 페이로드 |

---

#### 5.1.4 Request-Response RPC 전송

`sendRequest(rpcId, payloadBytes, sendFn, timeoutMs?)` 로 요청을 보내고 응답을 `Promise`로 대기합니다.

```javascript
import { decodePowerManagerPowerStatus, encodePowerManagerGetPowerStatusRequest }
    from './windrpc/WindRpcClient.js';

// RPC ID: 서비스 8 (0x08), RPC 1 (0x01) -> 0x0801
const RPC_GET_POWER_STATUS = 0x0801;

async function readPowerStatus() {
    // 1. 요청 페이로드 인코딩 (Empty의 경우 빈 Uint8Array)
    const reqPayload = encodePowerManagerGetPowerStatusRequest({});

    // 2. 전송 후 응답 대기
    const responseFrame = await client.sendRequest(
        RPC_GET_POWER_STATUS,
        reqPayload,
        (frame) => serialPort.write(frame), // sendFn: 실제 전송 방법
        3000                                 // 타임아웃(ms), 기본값: 2000
    );

    // 3. 응답 페이로드 디코딩
    const status = decodePowerManagerPowerStatus(responseFrame.payload);
    console.log(`전압: ${status.voltage_mv} mV, 충전 중: ${status.is_charging}`);
    return status;
}
```

> **오류 처리**: `sendRequest`는 타임아웃이나 서버가 `RPC_ID 0x0000`(시스템 에러)을 반환하면 Promise를 reject합니다.

```javascript
try {
    const status = await readPowerStatus();
} catch (err) {
    console.error('RPC 실패:', err.message);
}
```

#### 5.1.5 Notification 수신 (서버 푸시)

Notification은 클라이언트가 미리 이벤트 핸들러를 등록(구독, Subscription)한 후, 서버(MCU)에서 특정 조건이나 이벤트가 발생할 때 비동기로 Push 전송되는 이벤트입니다. 수신 데이터는 `receiveBytes` / `receiveRawDatagram`에 등록된 `onNotification` 구독 콜백에서 디스패치되어 처리됩니다.

```javascript
import { decodePowerManagerPowerStatus } from './windrpc/WindRpcClient.js';

// RPC ID: 서비스 8 (0x08), 이벤트 RPC 2, MSB 세트 (0x82) -> 0x0882
const RPC_CHARGING_ALERT = 0x0882;

function handleNotification(notification) {
    const { rpcId, payload } = notification;

    if (rpcId === RPC_CHARGING_ALERT) {
        const alert = decodePowerManagerPowerStatus(payload);
        console.log(`[알림] 충전 상태 변경: ${alert.is_charging}`);
    }
}

serialPort.on('data', (chunk) => {
    client.receiveBytes(chunk, handleNotification);
});
```

> **Notification RPC ID 규칙**: 이벤트 ID는 하위 바이트의 bit 7이 세트됩니다 (`rpc_id | 0x80`). 서비스 8, RPC ID 2 → `(0x08 << 8) | (0x02 | 0x80)` = `0x0882`.

---

#### 5.1.6 Ping & 버전 핸드셰이크

`ping` (RPC ID `0x0601`)을 전송하면 코어/스펙 버전 정보를 수신하여 자동으로 로그에 출력합니다.

```javascript
// 클라이언트는 0x0601 수신 시 PingResponse를 자동 디코딩하여 로그 출력합니다.
// ping 프레임 직접 전송:
const pingFrame = client.buildCobsFrame(0x0601);
serialPort.write(pingFrame);

// sendRequest로 PingResponse를 명시적으로 await 하는 방법:
const pingResp = await client.sendRequest(
    0x0601,
    new Uint8Array(0),
    (frame) => serialPort.write(frame)
);
// pingResp.payload에 원시 PingResponse protobuf 바이트가 담겨 있습니다.
```

---

#### 5.1.7 어큐뮬레이터 리셋

시리얼 연결이 리셋되거나 스트림이 손상된 경우 `resetAccumulator()`를 호출하여 내부 수신 버퍼와 대기 중인 모든 요청을 초기화합니다.

```javascript
serialPort.on('close', () => {
    client.resetAccumulator();
});
```

---

### 5.2 C# WinForms / .NET SDK

#### 5.2.1 생성

```bash
windrpc client -s user_spec.yml -o Communication/WindRpc --lang csharp
```

생성 결과물:
- `WindRpcClient.cs` — 트랜스포트 독립 RPC 클라이언트 (`RpcHandler`)
- `Generated/*.cs` — `.proto` 스키마로부터 컴파일된 Protobuf 데이터 클래스

> **사전 요건**: `protoc`가 `PATH`에 설치되어 있어야 합니다 (예: `choco install protoc`). 생성기가 자동으로 `protoc`를 호출하여 `.proto` → `.cs` 컴파일을 수행합니다.

---

#### 5.2.2 프로젝트 설정

생성된 파일을 `.csproj`에 포함하고 NuGet 패키지를 설치합니다:

```bash
dotnet add package Google.Protobuf
```

`Generated/*.cs` 파일들은 프로젝트 디렉터리 내에 있으면 자동으로 빌드에 포함됩니다.

---

#### 5.2.3 인스턴스 생성 & 트랜스포트 바인딩

`RpcHandler`는 송신 델리게이트 `Func<byte[], Task>`를 생성자에서 받고, `ReceiveBytes(byte[])` 메서드로 수신 데이터를 주입합니다.

```csharp
using HilightBox.Communication.WindRpc;

// 송신 델리게이트로 핸들러 생성
var rpcHandler = new RpcHandler(async (frame) =>
{
    await serialPort.BaseStream.WriteAsync(frame, 0, frame.Length);
});

// 수신 데이터 주입 (시리얼 DataReceived 이벤트에서 호출)
serialPort.DataReceived += (s, e) =>
{
    var buf = new byte[serialPort.BytesToRead];
    serialPort.Read(buf, 0, buf.Length);
    rpcHandler.ReceiveBytes(buf);
};
```

---

#### 5.2.4 Request-Response RPC 전송

```csharp
using Google.Protobuf;
using MyProject.Windrpc.Service.PowerManager;

public class PowerService
{
    private readonly RpcHandler _rpcHandler;

    public PowerService(RpcHandler handler) => _rpcHandler = handler;

    public async Task<PowerStatus> GetPowerStatusAsync()
    {
        // RPC ID: 서비스 8 (0x08), RPC 1 (0x01) -> 0x0801
        const int RpcId = 0x0801;

        // 빈 페이로드로 요청 전송
        var response = await _rpcHandler.SendRequestAsync(
            RpcId,
            ByteString.Empty.ToByteArray(),
            timeoutMs: 3000);

        // 응답 페이로드를 Protobuf 메시지로 파싱
        return PowerStatus.Parser.ParseFrom(response.Payload);
    }
}
```

---

#### 5.2.5 Notification 수신 (서버 푸시)

`RpcHandler`의 `OnNotification` 이벤트에 핸들러를 등록합니다:

```csharp
using MyProject.Windrpc.Service.PowerManager;

// RPC ID: 서비스 8 (0x08), 이벤트 RPC 2 (0x02 | 0x80) -> 0x0882
const int RpcChargingAlert = 0x0882;

rpcHandler.OnNotification += (notification) =>
{
    if (notification.RpcId == RpcChargingAlert)
    {
        var alert = PowerStatus.Parser.ParseFrom(notification.Payload);
        Console.WriteLine($"[알림] 충전: {alert.IsCharging}, 전압: {alert.VoltageMv} mV");
    }
};
```

---

#### 5.2.6 Ping & 버전 핸드셰이크

```csharp
using MyProject.Windrpc.Core; // PingResponse는 core 패키지에 있습니다

public async Task PingAsync()
{
    var response = await _rpcHandler.SendRequestAsync(
        0x0601,
        Array.Empty<byte>());

    var pingResponse = PingResponse.Parser.ParseFrom(response.Payload);
    Console.WriteLine($"코어: {pingResponse.CoreVersionName} ({pingResponse.CoreVersionCode})");
    Console.WriteLine($"스펙: {pingResponse.SpecVersionName} ({pingResponse.SpecVersionCode})");
}
```

---

#### 5.2.7 타임아웃 & 오류 처리

`SendRequestAsync`는 지정 시간 내 응답이 없으면 `TimeoutException`, 서버가 오류 상태(RPC ID `0x0000`)를 반환하면 `RpcException`을 던집니다.

```csharp
try
{
    var status = await _powerService.GetPowerStatusAsync();
}
catch (TimeoutException)
{
    Console.Error.WriteLine("RPC 타임아웃.");
}
catch (RpcException ex)
{
    Console.Error.WriteLine($"RPC 오류: {ex.StatusCode} - {ex.Message}");
}
```

---

### 5.3 Python Client SDK (`WindRpcClient.py`)

#### 5.3.1 생성

```bash
windrpc client -s user_spec.yml -o client/python -l python
```

생성 결과물:
- `WindRpcClient.py` — 단일 파일 파이썬 클라이언트 SDK (`WindRpcClient` 클래스, COBS 인코딩/디코딩, 6바이트 바이너리 헤더 처리, `asyncio` 비동기 API)
- `Generated/*_pb2.py` — `.proto` 스키마로부터 컴파일된 Python Protobuf 데이터 클래스
- `Protos/*.proto` — 참조용 Protobuf 스키마 및 `.options` 파일

#### 5.3.2 수신 및 바인딩 (Raw Datagram / Byte Stream)

```python
import asyncio
from WindRpcClient import WindRpcClient, RPC_POWER_MANAGER_GET_POWER_STATUS, RPC_POWER_MANAGER_CHARGING_ALERT
from my_package.windrpc.service import power_manager_pb2

client = WindRpcClient()

# Datagram 채널 (UDP / BLE):
def on_udp_rx(data):
    client.receive_raw_datagram(data, on_notification=handle_notification)

# Byte Stream 채널 (UART / COBS):
def on_uart_rx(chunk):
    client.receive_bytes(chunk, on_notification=handle_notification)
```

#### 5.3.3 Request-Response 비동기 호출 (`asyncio`)

```python
async def fetch_power_status(transport_send_fn):
    response_frame = await client.send_request_async(
        RPC_POWER_MANAGER_GET_POWER_STATUS,
        b"", # 요청 페이로드
        transport_send_fn,
        timeout_ms=3000
    )
    status = power_manager_pb2.PowerStatus()
    status.ParseFromString(response_frame.payload)
    return status
```

#### 5.3.4 Notification 수신 (서버 푸시)

```python
def handle_notification(frame):
    if frame.rpc_id == RPC_POWER_MANAGER_CHARGING_ALERT:
        alert = power_manager_pb2.PowerStatus()
        alert.ParseFromString(frame.payload)
        print(f"[알림] 충전: {alert.is_charging}, 전압: {alert.voltage_mv} mV")
```

---

## 6. CLI 명령 레퍼런스

```bash
# 1. 프로토 스키마 및 nanopb 옵션 독립 생성 (.proto, .options)
windrpc proto -s user_spec.yml -o protos

# 2. C 서버 연동 코드 생성 (내부적으로 .proto 생성 포함)
windrpc server -s user_spec.yml -o server

# 3. JavaScript / TypeScript 클라이언트 SDK 생성 (내부적으로 .proto 생성 포함)
windrpc client -s user_spec.yml -o client/js -l js

# 4. C# 클라이언트 SDK 생성 (내부적으로 .proto 생성 포함)
windrpc client -s user_spec.yml -o client/csharp -l csharp

# 5. Python 클라이언트 SDK 생성 (내부적으로 .proto 생성 포함)
windrpc client -s user_spec.yml -o client/python -l python
```
