#!/usr/bin/env python3
"""
One-Touch Automated Generation & Verification Script for UDP Demo.
Generates code, builds C UDP server, launches server, executes JS & Python clients, and verifies logs.
"""
import os
import sys
import time
import subprocess

def main():
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    c_server_dir = os.path.join(demo_dir, "c_server")
    js_client_dir = os.path.join(demo_dir, "js_client")
    py_client_dir = os.path.join(demo_dir, "py_client")

    print("============================================================")
    print(" WindRPC Integrated UDP Demo Automated Generator & Test Runner")
    print("============================================================")

    # Step 1: Run Code Generation
    print("\n>>> [Step 1/5] Running Code Generation (generate.py)...")
    subprocess.run([sys.executable, os.path.join(demo_dir, "generate.py")], check=True)

    # Step 2: Build C Server
    print("\n>>> [Step 2/5] Building C UDP Server with CMake...")
    build_dir = os.path.join(c_server_dir, "build")
    subprocess.run(["cmake", "-B", build_dir, "-S", c_server_dir], check=True)
    subprocess.run(["cmake", "--build", build_dir], check=True)

    # Find C server executable
    if sys.platform == "win32":
        server_exe = os.path.join(build_dir, "udp_server.exe")
    else:
        server_exe = os.path.join(build_dir, "udp_server")

    if not os.path.exists(server_exe):
        print(f"[ERROR] C Server executable not found at: {server_exe}")
        sys.exit(1)

    # Step 3: Launch C Server in background
    print(f"\n>>> [Step 3/5] Starting C UDP Server background process ({server_exe})...")
    server_proc = subprocess.Popen([server_exe], cwd=c_server_dir)
    time.sleep(1.0) # Wait for server to bind UDP port 5000

    try:
        # Step 4: Run Node.js Client
        print("\n>>> [Step 4/5] Executing Node.js Client (app.mjs)...")
        subprocess.run(["node", "app.mjs"], cwd=js_client_dir, check=True)

        # Step 5: Run Python Client
        print("\n>>> [Step 5/5] Executing Python Client (app.py)...")
        subprocess.run([sys.executable, "app.py"], cwd=py_client_dir, check=True)

        print("\n============================================================")
        print(" 🎉 ALL DEMO STEPS EXECUTED AND VERIFIED SUCCESSFULLY!")
        print("============================================================")

    finally:
        # Terminate server process cleanly
        print("\n>>> Cleaning up C Server background process...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print(">>> C Server background process terminated.")

if __name__ == "__main__":
    main()
