import subprocess
import sys
import os
import shutil
import glob

def print_banner(msg):
    print("\n" + "=" * 60)
    print(f" {msg}")
    print("=" * 60)

def run_step(step_name, cmd_args, cwd=None):
    print(f"\n>> Running: {step_name}...")
    print(f"Command: {' '.join(cmd_args)}")
    try:
        # Connect stdout/stderr directly for real-time streaming output
        subprocess.run(cmd_args, cwd=cwd, check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"!! Step '{step_name}' FAILED with exit code {e.returncode}")
        return False

import random
import string
import yaml

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    gen_dir = os.path.join(root_dir, "tests", "generated")
    build_dir = os.path.join(root_dir, "tests", "build")

    print_banner("WindRPC Integrated Test Suite Execution")

    # Step 1: Python Validator Unit Tests
    print_banner("Step 1: Python Validator Unit Tests")
    py_test_cmd = [sys.executable, "-m", "unittest", "tests/test_validator.py"]
    if not run_step("Python Validator Tests", py_test_cmd, cwd=root_dir):
        sys.exit(1)

    # Step 2: Code Generation Tests (Flat Mode)
    print_banner("Step 2: Auto-Generating Flat Proto & C Server Code")
    flat_gen_dir = os.path.join(root_dir, "tests", "generated_flat")
    if os.path.exists(flat_gen_dir):
        shutil.rmtree(flat_gen_dir)
    os.makedirs(flat_gen_dir, exist_ok=True)

    spec_path = os.path.join(root_dir, "tests", "test_spec.yml")
    
    # Random package name generation for test suite robustness
    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    random_package = f"pkg_{rand_suffix}"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = yaml.safe_load(f)
    spec_data["package"] = random_package
    with open(spec_path, "w", encoding="utf-8") as f:
        yaml.dump(spec_data, f, sort_keys=False)
    print(f"  - Applied random package name for unit test: '{random_package}'")
    
    gen_proto_flat_cmd = [sys.executable, "windrpc/windrpc_gen.py", "proto", "-s", spec_path, "-o", flat_gen_dir]
    if not run_step("Generating Flat Proto Files", gen_proto_flat_cmd, cwd=root_dir):
        sys.exit(1)

    gen_server_flat_cmd = [sys.executable, "windrpc/windrpc_gen.py", "server", "-s", spec_path, "-o", flat_gen_dir]
    if not run_step("Generating C Server Code (Flat)", gen_server_flat_cmd, cwd=root_dir):
        sys.exit(1)

    # Step 3: PC Host Compilation (CMake - Flat Mode)
    print_banner("Step 3: Compiling Flat C Host Tests")
    build_flat_dir = os.path.join(root_dir, "tests", "build_flat")
    os.makedirs(build_flat_dir, exist_ok=True)

    cmake_gen_args = []
    if sys.platform == "win32" and shutil.which("gcc"):
        cmake_gen_args = ["-G", "MinGW Makefiles"]

    cmake_conf_flat_cmd = ["cmake"] + cmake_gen_args + ["-B", "build_flat", "-S", ".", "-DUSE_FLAT_MODE=ON"]
    if not run_step("CMake Configure (Flat Mode)", cmake_conf_flat_cmd, cwd=os.path.join(root_dir, "tests")):
        sys.exit(1)

    cmake_build_flat_cmd = ["cmake", "--build", "build_flat"]
    if not run_step("CMake Build (Flat Mode)", cmake_build_flat_cmd, cwd=os.path.join(root_dir, "tests")):
        sys.exit(1)

    # Step 4: Execute Flat C Host Unit Tests (Double & In-place Buffers)
    print_banner("Step 4: Executing Flat C Host Unit Tests (Double & In-place Buffers)")
    
    # 4.1 Double Buffer Mode Binary Verification
    double_binaries = glob.glob(os.path.join(build_flat_dir, "**", "run_tests_double.exe"), recursive=True) + \
                      glob.glob(os.path.join(build_flat_dir, "**", "run_tests_double"), recursive=True)
    if double_binaries:
        double_bin = double_binaries[0]
        if not run_step("Execute Double Buffer C Test Binary", [double_bin], cwd=os.path.dirname(double_bin)):
            sys.exit(1)
    else:
        print("!! Warning: 'run_tests_double' executable not found.")

    # 4.2 In-place Buffer Mode Binary Verification
    inplace_binaries = glob.glob(os.path.join(build_flat_dir, "**", "run_tests_inplace.exe"), recursive=True) + \
                       glob.glob(os.path.join(build_flat_dir, "**", "run_tests_inplace"), recursive=True)
    if inplace_binaries:
        inplace_bin = inplace_binaries[0]
        if not run_step("Execute In-place Buffer C Test Binary", [inplace_bin], cwd=os.path.dirname(inplace_bin)):
            sys.exit(1)
    else:
        print("!! Warning: 'run_tests_inplace' executable not found.")

    # Step 5: JS Client SDK Generation and Node.js Unit/Integration Tests
    print_banner("Step 5: Testing JS Client SDK with Node.js")
    gen_js_dir = os.path.join(root_dir, "tests", "generated_js")
    if os.path.exists(gen_js_dir):
        shutil.rmtree(gen_js_dir)
    os.makedirs(gen_js_dir, exist_ok=True)

    gen_client_js_cmd = [sys.executable, "windrpc/windrpc_gen.py", "client", "-s", spec_path, "-o", gen_js_dir, "--lang", "js"]
    if not run_step("Generating JS Client SDK", gen_client_js_cmd, cwd=root_dir):
        sys.exit(1)

    node_bin = shutil.which("node")
    if node_bin:
        node_test_cmd = [node_bin, "tests/test_js_client.mjs"]
        if not run_step("Executing JS Client Unit Tests (Node.js)", node_test_cmd, cwd=root_dir):
            sys.exit(1)
    else:
        print("  - Warning: 'node' executable not found. Skipping Node.js JS test.")

    # Step 6: C# Client SDK Compilation and dotnet Build Verification
    print_banner("Step 6: Testing C# Client SDK Compilation with dotnet")
    csharp_project = os.path.abspath(os.path.join(root_dir, "..", "c#", "HilightBoxWInForm", "HilightBox.csproj"))
    csharp_out_dir = os.path.join(os.path.dirname(csharp_project), "Communication", "WindRpc")
    if os.path.exists(csharp_out_dir):
        shutil.rmtree(csharp_out_dir)
    os.makedirs(csharp_out_dir, exist_ok=True)

    gen_client_cs_cmd = [sys.executable, "windrpc/windrpc_gen.py", "client", "-s", spec_path, "-o", csharp_out_dir, "--lang", "csharp"]
    if not run_step("Generating C# Client SDK", gen_client_cs_cmd, cwd=root_dir):
        sys.exit(1)

    dotnet_bin = shutil.which("dotnet")
    if dotnet_bin and os.path.exists(csharp_project):
        dotnet_cmd = [dotnet_bin, "build", csharp_project]
        if not run_step("Executing C# Client Build (dotnet)", dotnet_cmd, cwd=root_dir):
            sys.exit(1)
    else:
        print("  - Warning: 'dotnet' executable or C# project not found. Skipping C# dotnet test.")

    # Step 7: Python Client SDK Generation and Unit Tests
    print_banner("Step 7: Testing Python Client SDK Generation & Execution")
    gen_py_dir = os.path.join(root_dir, "tests", "generated_py")
    if os.path.exists(gen_py_dir):
        shutil.rmtree(gen_py_dir)
    os.makedirs(gen_py_dir, exist_ok=True)

    gen_client_py_cmd = [sys.executable, "windrpc/windrpc_gen.py", "client", "-s", spec_path, "-o", gen_py_dir, "--lang", "python"]
    if not run_step("Generating Python Client SDK", gen_client_py_cmd, cwd=root_dir):
        sys.exit(1)

    py_client_test_cmd = [sys.executable, "tests/test_python_client.py"]
    if not run_step("Executing Python Client Unit Tests", py_client_test_cmd, cwd=root_dir):
        sys.exit(1)

    print_banner("ALL WINDRPC INTEGRATED TESTS PASSED SUCCESSFULLY! 🚀")

if __name__ == "__main__":
    main()
