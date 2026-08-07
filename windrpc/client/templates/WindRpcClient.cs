using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Google.Protobuf;
// --WINDRPC_CLIENT_IMPORTS

namespace --WINDRPC_CLIENT_NAMESPACE
{
    public class WindRpcClient : IDisposable
    {
// --WINDRPC_RPC_ID_CONSTANTS

// --WINDRPC_SUB_CLIENT_PROPERTIES

        // Standalone COBS utilities
        public static byte[] CobsEncode(ReadOnlySpan<byte> data) => Cobs.Encode(data);
        public static byte[] CobsDecode(ReadOnlySpan<byte> data) => Cobs.Decode(data);

        private readonly RpcHandler _handler;
        public bool IsConnected => _handler.IsConnected;

        public event EventHandler? ChannelLost
        {
            add    => _handler.ChannelLost += value;
            remove => _handler.ChannelLost -= value;
        }

        public WindRpcClient(ICommChannel channel)
        {
            _handler = new RpcHandler(channel);
// --WINDRPC_SUB_CLIENT_INIT
            _handler.PacketReceived += OnPacketReceived;
        }

        public void Connect()    => _handler.Connect();
        public void Disconnect() => _handler.Disconnect();

        public void Dispose()
        {
            _handler.PacketReceived -= OnPacketReceived;
            _handler.Dispose();
        }

        private void OnPacketReceived(object? sender, FlatPacket packet)
        {
            switch (packet.RpcId)
            {
// --WINDRPC_NOTIFICATION_DISPATCH
                default:
                    Debug.WriteLine($"WindRpcClient: unhandled notification rpcId=0x{packet.RpcId:X4}");
                    break;
            }
        }

// --WINDRPC_SERVICE_CLIENT_CLASSES
    }
}

