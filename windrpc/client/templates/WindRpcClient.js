import protobuf from 'protobufjs';

export function cobsEncode(inputData) {
    const input = (inputData && inputData.length !== undefined) ? Uint8Array.from(inputData) : new Uint8Array(inputData || 0);
    const output = [];
    let codeIndex = 0;
    let code = 1;

    output.push(0);

    for (let i = 0; i < input.length; i++) {
        if (input[i] !== 0) {
            output.push(input[i]);
            code++;
        }

        if (input[i] === 0 || code === 0xFF) {
            output[codeIndex] = code;
            codeIndex = output.length;
            output.push(0);
            code = 1;
        }
    }

    output[codeIndex] = code;
    return new Uint8Array(output);
}

export function cobsDecode(inputData) {
    const input = (inputData && inputData.length !== undefined) ? Uint8Array.from(inputData) : new Uint8Array(inputData || 0);
    const output = [];
    let i = 0;

    while (i < input.length) {
        let code = input[i];
        if (code === 0) break;

        i++;
        for (let j = 1; j < code; j++) {
            if (i < input.length) {
                output.push(input[i++]);
            }
        }

        if (code < 0xFF && i < input.length && input[i] !== 0) {
            output.push(0);
        }
    }

    return new Uint8Array(output);
}

export const RPC_ID = {
// --WINDRPC_RPC_ID_CONSTANTS
};

export const PROTO_SCHEMA = // --WINDRPC_PROTO_SCHEMA;

const root = protobuf.Root.fromJSON(PROTO_SCHEMA);

// --WINDRPC_MESSAGE_HELPERS

export class WindRpcClient {
    constructor() {
        this.seqId = 0;
        this._pendingRequests = new Map();
        this._rxAccumulator = [];
// --WINDRPC_SUB_CLIENT_INIT
    }

    // Standalone COBS utilities
    static cobsEncode(data) { return cobsEncode(data); }
    static cobsDecode(data) { return cobsDecode(data); }
    cobsEncode(data) { return cobsEncode(data); }
    cobsDecode(data) { return cobsDecode(data); }

    getNextSeqId() {
        this.seqId = (this.seqId + 1) & 0xFFFF;
        return this.seqId;
    }

    resetAccumulator() {
        this._rxAccumulator = [];
        for (const [seqId, pending] of this._pendingRequests.entries()) {
            pending.reject(new Error('Transport reset'));
        }
        this._pendingRequests.clear();
    }

    buildFrame(rpcId, payloadBytes = new Uint8Array(0)) {
        return this.buildRawFrame(rpcId, payloadBytes);
    }

    // Build raw frame: [RPC_ID:2][SEQ_ID:2][PAYLOAD_LEN:2] + PAYLOAD
    buildRawFrame(rpcId, payloadBytes = new Uint8Array(0)) {
        const seqId = this.getNextSeqId();
        const payloadLen = payloadBytes.length;
        const header = new Uint8Array(6);
        header[0] = rpcId & 0xFF;
        header[1] = (rpcId >> 8) & 0xFF;
        header[2] = seqId & 0xFF;
        header[3] = (seqId >> 8) & 0xFF;
        header[4] = payloadLen & 0xFF;
        header[5] = (payloadLen >> 8) & 0xFF;

        const rawPacket = new Uint8Array(6 + payloadLen);
        rawPacket.set(header, 0);
        if (payloadLen > 0) rawPacket.set(payloadBytes, 6);
        return rawPacket;
    }

    // Build COBS framed packet: [COBS_DATA] + 0x00
    buildCobsFrame(rpcId, payloadBytes = new Uint8Array(0)) {
        const rawPacket = this.buildRawFrame(rpcId, payloadBytes);
        const encoded = cobsEncode(rawPacket);
        const framed = new Uint8Array(encoded.length + 1);
        framed.set(encoded, 0);
        framed[encoded.length] = 0;
        return framed;
    }

    // Process raw UDP/datagram packet directly
    receiveRawDatagram(bytes, onNotification) {
        if (!bytes) return;
        const decoded = (bytes instanceof Uint8Array) ? bytes : new Uint8Array(bytes);
        if (decoded && decoded.length >= 6) {
            this._dispatchFrame(decoded, onNotification);
        }
    }

    receiveFrame(frame, onNotification) {
        this.receiveRawDatagram(frame, onNotification);
    }

    // Accumulate stream bytes until 0x00 delimiter, then decode COBS
    receiveBytes(bytes, onNotification) {
        if (!bytes) return;
        const incoming = (bytes instanceof Uint8Array) ? bytes : new Uint8Array(bytes);
        for (let i = 0; i < incoming.length; i++) {
            const b = incoming[i];
            if (b === 0x00) {
                if (this._rxAccumulator.length > 0) {
                    const cobsPacket = new Uint8Array(this._rxAccumulator);
                    this._rxAccumulator = [];
                    try {
                        const decoded = cobsDecode(cobsPacket);
                        if (decoded && decoded.length >= 6) {
                            this._dispatchFrame(decoded, onNotification);
                        }
                    } catch (err) {
                        console.warn('[WindRPC] COBS decode error:', err);
                    }
                }
            } else {
                this._rxAccumulator.push(b);
                if (this._rxAccumulator.length > 4096) {
                    this._rxAccumulator = [];
                }
            }
        }
    }

    _dispatchFrame(decoded, onNotification) {
        if (decoded.length < 6) return;
        const rpcId = decoded[0] | (decoded[1] << 8);
        const seqId = decoded[2] | (decoded[3] << 8);
        const payLen = decoded[4] | (decoded[5] << 8);
        const payload = decoded.slice(6, 6 + payLen);

        if (rpcId === 0x0601) {
            try {
                const pingResp = (typeof decodePingResponse === 'function') ? decodePingResponse(payload) : null;
                if (pingResp) {
                    console.log(`[WindRPC Ping Response] Core: v${pingResp.coreVersionName || '0.1.0'} (${pingResp.coreVersionCode ?? 100}), Spec: v${pingResp.specVersionName || '1.0.0'} (${pingResp.specVersionCode ?? 10000})`);
                }
            } catch (err) {
                // ignore
            }
        }

        const pending = this._pendingRequests.get(seqId);
        if (pending) {
            this._pendingRequests.delete(seqId);
            if (rpcId === 0x0000) {
                try {
                    const status = (typeof decodeStatus === 'function') ? decodeStatus(payload) : { code: -1, message: 'Server error' };
                    pending.reject(new Error(`[WindRPC Status Error ${status.code}] ${status.message || 'Server error'}`));
                } catch (err) {
                    pending.reject(new Error(`[WindRPC Status Error] Unknown server error (rpcId=0x0000)`));
                }
            } else {
                pending.resolve({ rpcId, seqId, payload });
            }
            return;
        }

        if (onNotification && typeof onNotification === 'function') {
            onNotification({ rpcId, seqId, payload });
        }
    }

    sendRequest(rpcId, payloadBytes, sendFn, timeoutMs = 2000) {
        const frame = this.buildFrame(rpcId, payloadBytes);
        const reqSeqId = this.seqId;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                this._pendingRequests.delete(reqSeqId);
                reject(new Error(`RPC timeout: rpcId=0x${rpcId.toString(16)}`));
            }, timeoutMs);
            this._pendingRequests.set(reqSeqId, {
                resolve: (v) => { clearTimeout(timer); resolve(v); },
                reject:  (e) => { clearTimeout(timer); reject(e); },
            });
            sendFn(frame);
        });
    }
}

// --WINDRPC_SERVICE_CLIENT_CLASSES

export const windRpcClient = new WindRpcClient();

