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
        # 실시간 스트리밍 출력을 위해 stdout/stderr 파이프를 제거하고 직결
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

    # 1단계: 파이썬 Validator 유닛 테스트 실행
    print_banner("Step 1: Python Validator Unit Tests")
    py_test_cmd = [sys.executable, "-m", "unittest", "tests/test_validator.py"]
    if not run_step("Python Validator Tests", py_test_cmd, cwd=root_dir):
        sys.exit(1)

    # 2단계: 코드 제너레이션 테스트
    print_banner("Step 2: Auto-Generating Proto & C Server Code")
    # 기존 생성 폴더 정리
    if os.path.exists(gen_dir):
        shutil.rmtree(gen_dir)
    os.makedirs(gen_dir, exist_ok=True)

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
    
    # 2.1 proto 생성
    gen_proto_cmd = [sys.executable, "windrpc/windrpc_gen.py", "proto", "-s", spec_path, "-o", gen_dir]
    if not run_step("Generating Proto Files", gen_proto_cmd, cwd=root_dir):
        sys.exit(1)
        
    # 2.2 server c 코드 생성
    gen_server_cmd = [sys.executable, "windrpc/windrpc_gen.py", "server", "-s", spec_path, "-o", gen_dir]
    if not run_step("Generating C Server Code", gen_server_cmd, cwd=root_dir):
        sys.exit(1)

    # 2.3 테스트용 windrpc_config.h 수정 (request_id 활성화)
    config_path = os.path.join(gen_dir, "windrpc_config.h")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("WINDRPC_REQUEST_ID_TYPE_NONE", "WINDRPC_REQUEST_ID_TYPE_BYTES")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  - Updated windrpc_config.h to enable request_id validation.")

    # CMakeCache.txt 삭제하여 캐시 꼬임 예방 (Windows .git 권한 에러 우회용 Clean Build)
    cache_path = os.path.join(build_dir, "CMakeCache.txt")
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            print("  - Removed CMakeCache.txt to enforce clean compilation.")
        except Exception as e:
            print(f"  - Warning: Could not remove CMakeCache.txt: {e}")

    # 3단계: PC 호스트 컴파일 (CMake)
    print_banner("Step 3: Compiling C Host Tests")
    # 기존 빌드 폴더가 존재하면 덮어쓰기 형태로 실행 (Windows .git 권한 에러 회피)
    os.makedirs(build_dir, exist_ok=True)

    # 3.1 CMake Configure
    cmake_conf_cmd = ["cmake", "-B", "build", "-S", "."]
    if not run_step("CMake Configure", cmake_conf_cmd, cwd=os.path.join(root_dir, "tests")):
        sys.exit(1)

    # 3.2 CMake Build
    cmake_build_cmd = ["cmake", "--build", "build"]
    if not run_step("CMake Build", cmake_build_cmd, cwd=os.path.join(root_dir, "tests")):
        sys.exit(1)

    # 4단계: C 테스트 바이너리 실행
    print_banner("Step 4: Executing C Host Unit Tests")
    
    # MSVC, MinGW, Makefiles 등 컴파일러/플랫폼에 따라 바이너리 생성 위치가 다를 수 있으므로 검색함
    search_pattern = os.path.join(build_dir, "**", "run_tests.exe")
    found_binaries = glob.glob(search_pattern, recursive=True)
    
    # Unix 계열도 대응할 수 있도록 확장자 없는 경우 추가 매칭
    if not found_binaries:
        search_pattern_unix = os.path.join(build_dir, "**", "run_tests")
        found_binaries = glob.glob(search_pattern_unix, recursive=True)

    if not found_binaries:
        print("!! Error: C Test executable 'run_tests' not found in build directory.")
        sys.exit(1)

    test_bin_path = found_binaries[0]
    print(f"Found test executable: {test_bin_path}")

    # 바이너리 실행
    if not run_step("C Host Unit Tests Execution", [test_bin_path]):
        sys.exit(1)

    print_banner("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
