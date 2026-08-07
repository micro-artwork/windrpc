import assert from 'node:assert';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const generatedDir = path.join(__dirname, 'generated_js');

// Dynamically import generated JS SDK files using file:// URLs
const clientPath = pathToFileURL(path.join(generatedDir, 'WindRpcClient.js')).href;

const { windRpcClient, WindRpcClient, RPC_ID, cobsEncode, cobsDecode } = await import(clientPath);

console.log("=== Step 6.1: Running COBS Unit Tests ===");

// 1. COBS Unit Tests
function testCobsRoundtrip(name, rawBytes) {
    const encoded = cobsEncode(rawBytes);
    assert(encoded instanceof Uint8Array, `${name}: encoded should be Uint8Array`);
    
    // Decoded bytes
    const decoded = cobsDecode(encoded);
    assert(decoded instanceof Uint8Array, `${name}: decoded should be Uint8Array`);
    assert.deepStrictEqual(Array.from(decoded), Array.from(rawBytes), `${name}: COBS roundtrip mismatch`);
    console.log(`  [PASS] COBS Test: ${name}`);
}

testCobsRoundtrip("Basic non-zero bytes", new Uint8Array([0x01, 0x02, 0x03, 0x04]));
testCobsRoundtrip("Single zero byte", new Uint8Array([0x00]));
testCobsRoundtrip("Multiple zero bytes", new Uint8Array([0x00, 0x00, 0x05, 0x00]));
testCobsRoundtrip("Single zero byte", new Uint8Array([0x00]));
testCobsRoundtrip("Multiple zero bytes", new Uint8Array([0x00, 0x00, 0x05, 0x00]));
testCobsRoundtrip("RPC Header + Zero payload", new Uint8Array([0x06, 0x01, 0x00, 0x01, 0x00, 0x00]));
testCobsRoundtrip("Node.js Buffer input compatibility", Buffer.from([0x06, 0x01, 0x00, 0x02, 0x00, 0x04, 0x00, 0x01, 0x00, 0x00]));

console.log("\n=== Step 6.2: Running WindRpcClient Frame Building Tests ===");

// 2. WindRpcClient Frame Building Tests
const testClient = new WindRpcClient();
const pingFrame = testClient.buildCobsFrame(RPC_ID.COMMON_PING);
assert(pingFrame instanceof Uint8Array, "pingFrame should be Uint8Array");
assert.strictEqual(pingFrame[pingFrame.length - 1], 0, "pingFrame should end with 0x00 delimiter");

// Decode COBS to inspect raw packet
const cleanPing = pingFrame.subarray(0, pingFrame.length - 1);
const rawPing = cobsDecode(cleanPing);
assert.strictEqual(rawPing.length, 6, "Raw Ping frame length should be 6 bytes");
assert.strictEqual(rawPing[0], 0x01, "RPC_ID Low byte should be 0x01");
assert.strictEqual(rawPing[1], 0x06, "RPC_ID High byte should be 0x06");
assert.strictEqual(rawPing[4], 0x00, "Payload length low byte should be 0");
assert.strictEqual(rawPing[5], 0x00, "Payload length high byte should be 0");
console.log("  [PASS] Ping Frame Generation & COBS Packaging OK");

console.log("\n=== Step 6.3: Running Request-Response RX Dispatch State Machine Tests ===");

// 3. Request-Response RX Dispatch Tests
let sentData = null;
const client = new WindRpcClient();

const reqPromise = client.sendRequest(RPC_ID.COMMON_PING, new Uint8Array(0), (framed) => {
    sentData = framed;
});

assert(sentData !== null, "sendFn should have received framed bytes");
assert.strictEqual(sentData[sentData.length - 1], 0, "Framed data must end with 0x00");

// Simulate MCU server COBS-encoded Ping response (Little-Endian header):
// Raw response: [0x01, 0x06, 0x01, 0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x00]
const mcuResponseRaw = new Uint8Array([0x01, 0x06, 0x01, 0x00, 0x04, 0x00, 0x00, 0x01, 0x00, 0x00]);
const mcuResponseCobsFrame = cobsEncode(mcuResponseRaw);
const mcuResponseCobs = new Uint8Array(mcuResponseCobsFrame.length + 1);
mcuResponseCobs.set(mcuResponseCobsFrame, 0);
mcuResponseCobs[mcuResponseCobsFrame.length] = 0;

// Feed simulated response into client.receiveBytes
client.receiveBytes(mcuResponseCobs);

const response = await reqPromise;
assert.strictEqual(response.rpcId, 0x0601, "Response RPC ID should be 0x0601");
assert.strictEqual(response.seqId, 1, "Response Seq ID should be 1");
assert.strictEqual(response.payload.length, 4, "Payload length should be 4 bytes");
console.log("  [PASS] Simulated MCU Ping Response Matched & Resolved Promise!");

console.log("\n=== Step 6.4: Running System Error Status (RPC ID 0x0000) Rejection Test ===");
const clientErr = new WindRpcClient();
const errPromise = clientErr.sendRequest(0x9999, new Uint8Array(0), () => {});

// MCU returns Status response: RPC_ID = 0x0000, SEQ_ID = 1, Payload = Status(code=12, message="Unimplemented")
// Raw packet: [0x00, 0x00, 0x01, 0x00, 0x02, 0x00, 0x08, 0x0C] (Status code 12)
const mcuErrCobs = cobsEncode(new Uint8Array([0x00, 0x00, 0x01, 0x00, 0x02, 0x00, 0x08, 0x0C]));
const framedErr = new Uint8Array(mcuErrCobs.length + 1);
framedErr.set(mcuErrCobs, 0);
framedErr[mcuErrCobs.length] = 0;

clientErr.receiveBytes(framedErr);

try {
    await errPromise;
    assert.fail("Should have rejected with System Error");
} catch (err) {
    assert(err.message.includes("WindRPC Status Error") || err.message.includes("12"), "Error message should contain status error code");
    console.log("  [PASS] Simulated System Error (0x0000) correctly rejected Promise with Status!");
}

console.log("\n=== Step 6.4: Running Notification RX Callback Tests ===");

let receivedNotification = null;
const notifClient = new WindRpcClient();

// Create notification COBS packet (RPC ID: 0x0C02, Seq: 0, PayLen: 3, Payload: [1, 2, 3])
const rawNotif = new Uint8Array([0x02, 0x0C, 0x00, 0x00, 0x03, 0x00, 0x01, 0x02, 0x03]);
const encodedNotif = cobsEncode(rawNotif);
const framedNotif = new Uint8Array(encodedNotif.length + 1);
framedNotif.set(encodedNotif, 0);
framedNotif[encodedNotif.length] = 0;

notifClient.receiveBytes(framedNotif, (notif) => {
    receivedNotification = notif;
});

assert(receivedNotification !== null, "Notification callback should be invoked");
assert.strictEqual(receivedNotification.rpcId, 0x0C02, "Notification RPC ID should be 0x0C02");
assert.deepStrictEqual(Array.from(receivedNotification.payload), [1, 2, 3], "Notification payload mismatch");
console.log("  [PASS] Notification Dispatch Callback OK!");

console.log("\nALL JS CLIENT TESTS PASSED SUCCESSFULLY! 🎉\n");
