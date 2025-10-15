# windrpc.py

import argparse
import sys
import os  # os 모듈을 임포트합니다.
from proto import generator as proto_generator
from server import generator as server_generator


def handle_proto_command(args):
    """'proto' 서브커맨드를 처리합니다."""
    print("--- Starting Protobuf Generation ---")

    # --- [수정] 경로 문제 해결 로직 ---
    # 1. windrpc_gen.py 스크립트가 있는 디렉토리의 절대 경로를 가져옵니다.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. 입력받은 스펙 파일 경로가 절대 경로가 아니면, 스크립트 위치 기준으로 경로를 조합합니다.
    core_spec_path = args.core_spec if os.path.isabs(
        args.core_spec) else os.path.join(script_dir, args.core_spec)
    user_spec_path = args.user_spec if os.path.isabs(
        args.user_spec) else os.path.join(script_dir, args.user_spec)

    # 3. 출력 디렉토리 경로도 동일하게 처리합니다.
    output_dir = args.output if os.path.isabs(
        args.output) else os.path.join(script_dir, args.output)

    # 4. 조합된 절대 경로를 사용하여 생성 함수를 호출합니다.
    proto_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        verbose=args.verbose
    )
    print("--- Protobuf Generation Finished ---")


def handle_server_command(args):
    """'server' 서브커맨드를 처리합니다."""
    print("--- Starting RPC Server Generation ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    core_spec_path = args.core_spec if os.path.isabs(
        args.core_spec) else os.path.join(script_dir, args.core_spec)
    user_spec_path = args.user_spec if os.path.isabs(
        args.user_spec) else os.path.join(script_dir, args.user_spec)
    output_dir = args.output if os.path.isabs(
        args.output) else os.path.join(script_dir, args.output)

    server_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        verbose=args.verbose)
    print("--- RPC Server Generation Finished ---")


def main():
    parser = argparse.ArgumentParser(
        description="WindRPC code generation tool.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(
        dest='command', required=True, help='Available commands')

    # --- 'proto' 서브커맨드 정의 ---
    proto_parser = subparsers.add_parser(
        'proto', help='Generate .proto files from YAML specifications.')
    proto_parser.add_argument(
        '-c', '--core-spec', default='core_spec.yml', help='Input core YAML spec file.')
    proto_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    proto_parser.add_argument(
        '-o', '--output', default='protos', help='Output directory for generated files.')
    proto_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    proto_parser.set_defaults(func=handle_proto_command)

    # --- 'server' 서브커맨드 정의 (추후 확장용) ---
    server_parser = subparsers.add_parser(
        'server', help='Generate RPC server C code (not yet implemented).')
    server_parser.add_argument(
        '-c', '--core-spec', default='core_spec.yml', help='Input core YAML spec file.')
    server_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    server_parser.add_argument(
        '-o', '--output', default='server', help='Output directory for generated files.')
    server_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    server_parser.set_defaults(func=handle_server_command)

    # 인수 파싱 및 기능 실행
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
