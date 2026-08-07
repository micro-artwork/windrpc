# tests/test_python_client.py
import os
import sys
import unittest

# Add generated_py directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gen_py_dir = os.path.join(root_dir, "tests", "generated_py")
sys.path.insert(0, gen_py_dir)

from WindRpcClient import WindRpcClient, cobs_encode, cobs_decode, WindRpcFrame


class TestPythonClientSdk(unittest.TestCase):

    def test_cobs_encode_decode(self):
        original = b"\x01\x00\x02\x00\x03"
        encoded = cobs_encode(original)
        self.assertTrue(encoded.endswith(b"\x00"))
        decoded = cobs_decode(encoded)
        self.assertEqual(original, decoded)

    def test_frame_pack_unpack(self):
        client = WindRpcClient()
        rpc_id = 0x0801
        seq_id = 42
        payload = b"Hello WindRPC"

        frame_bytes = client.pack_frame(rpc_id, seq_id, payload)
        self.assertEqual(len(frame_bytes), 6 + len(payload))

        unpacked = client.unpack_frame(frame_bytes)
        self.assertEqual(unpacked.rpc_id, rpc_id)
        self.assertEqual(unpacked.seq_id, seq_id)
        self.assertEqual(unpacked.payload, payload)

    def test_receive_raw_datagram(self):
        client = WindRpcClient()
        received_notifications = []

        def on_notification(frame):
            received_notifications.append(frame)

        # 1. Test notification (bit 7 set in low byte, e.g. 0x0882)
        notify_frame = client.pack_frame(0x0882, 0, b"Alert Payload")
        client.receive_raw_datagram(notify_frame, on_notification=on_notification)

        self.assertEqual(len(received_notifications), 1)
        self.assertEqual(received_notifications[0].rpc_id, 0x0882)
        self.assertEqual(received_notifications[0].payload, b"Alert Payload")


if __name__ == "__main__":
    unittest.main()
