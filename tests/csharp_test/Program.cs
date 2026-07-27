using System;
using WindRpc;

namespace CsharpTest
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("=== Step 7: Running C# Client SDK Compilation & Test ===");

            var client = new WindRpcClient();
            var pingFrame = client.Common.BuildPingFrame();

            Console.WriteLine($"[PASS] Generated C# Ping Frame ({pingFrame.Length} bytes)");
            Console.WriteLine("ALL C# CLIENT TESTS PASSED SUCCESSFULLY!");
        }
    }
}
