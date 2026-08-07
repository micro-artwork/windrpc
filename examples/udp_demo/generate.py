#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(demo_dir, "..", ".."))
    spec_path = os.path.join(demo_dir, "device_spec.yml")
    windrpc_gen = os.path.join(root_dir, "windrpc", "windrpc_gen.py")

    print("============================================================")
    print(" WindRPC One-Stop Code Generator for UDP Demo")
    print("============================================================")

    # 1. Generate C Server Proto & Engine Code
    c_out = os.path.join(demo_dir, "c_server", "generated")
    print(f"\n[1/4] Generating C Server Proto Files -> {c_out}")
    subprocess.run([sys.executable, windrpc_gen, "proto", "-s", spec_path, "-o", c_out], check=True)

    print(f"\n[2/4] Generating C Server Engine Code -> {c_out}")
    subprocess.run([sys.executable, windrpc_gen, "server", "-s", spec_path, "-o", c_out], check=True)

    # 2. Generate JS Client SDK
    js_out = os.path.join(demo_dir, "js_client", "generated")
    print(f"\n[3/4] Generating JS Client SDK -> {js_out}")
    subprocess.run([sys.executable, windrpc_gen, "client", "-s", spec_path, "-o", js_out, "-l", "js"], check=True)

    # 3. Generate Python Client SDK
    py_out = os.path.join(demo_dir, "py_client", "generated")
    print(f"\n[4/4] Generating Python Client SDK -> {py_out}")
    subprocess.run([sys.executable, windrpc_gen, "client", "-s", spec_path, "-o", py_out, "-l", "python"], check=True)

    print("\n============================================================")
    print(" SUCCESS! Code Generation Complete for C, JS, and Python.")
    print("============================================================")
    print(" Next Steps to Run Integrated Demo:")
    print(" 1) Build & Run C Server:")
    print("    cd c_server && cmake -B build -S . && cmake --build build")
    print("    ./build/udp_server (or .\\build\\udp_server.exe)")
    print(" 2) Run JS Client (Node.js):")
    print("    cd js_client && node app.mjs")
    print(" 3) Run Python Client:")
    print("    cd py_client && python app.py")
    print("============================================================")

if __name__ == "__main__":
    main()
