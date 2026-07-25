# windrpc_gen.py

import argparse
import sys
import os
from proto import generator as proto_generator
from server import generator as server_generator
from client import generator as client_generator


def handle_proto_command(args):
    """'proto' 서브커맨드를 처리합니다."""
    print("--- Starting Protobuf Generation ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    core_spec_path = args.core_spec if os.path.isabs(
        args.core_spec) else os.path.join(script_dir, args.core_spec)
    user_spec_path = args.user_spec if os.path.isabs(
        args.user_spec) else os.path.join(script_dir, args.user_spec)
    output_dir = args.output if os.path.isabs(
        args.output) else os.path.join(script_dir, args.output)

    proto_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        mode=args.mode,
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
        mode=args.mode,
        rtos=args.rtos,
        verbose=args.verbose)
    print("--- RPC Server Generation Finished ---")


def handle_client_command(args):
    """'client' 서브커맨드를 처리합니다."""
    print(f"--- Starting RPC Client Generation ({args.lang}) ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    core_spec_path = args.core_spec if os.path.isabs(
        args.core_spec) else os.path.join(script_dir, args.core_spec)
    user_spec_path = args.user_spec if os.path.isabs(
        args.user_spec) else os.path.join(script_dir, args.user_spec)
    output_dir = args.output if os.path.isabs(
        args.output) else os.path.join(script_dir, args.output)

    client_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        lang=args.lang,
        verbose=args.verbose)
    print("--- RPC Client Generation Finished ---")


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
        '-m', '--mode', choices=['nested', 'flat'], default=None, help='Envelope mode: flat (default) or nested.')
    proto_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    proto_parser.set_defaults(func=handle_proto_command)

    # --- 'server' 서브커맨드 정의 ---
    server_parser = subparsers.add_parser(
        'server', help='Generate RPC server C code.')
    server_parser.add_argument(
        '-c', '--core-spec', default='core_spec.yml', help='Input core YAML spec file.')
    server_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    server_parser.add_argument(
        '-o', '--output', default='server', help='Output directory for generated files.')
    server_parser.add_argument(
        '-m', '--mode', choices=['nested', 'flat'], default=None, help='Envelope mode: flat (default) or nested.')
    server_parser.add_argument(
        '-r', '--rtos', choices=['zephyr', 'freertos', 'none'], default='zephyr', help='Target RTOS (default: zephyr).')
    server_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    server_parser.set_defaults(func=handle_server_command)

    # --- 'client' 서브커맨드 정의 ---
    client_parser = subparsers.add_parser(
        'client', help='Generate RPC client SDK code (e.g. C#).')
    client_parser.add_argument(
        '-c', '--core-spec', default='core_spec.yml', help='Input core YAML spec file.')
    client_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    client_parser.add_argument(
        '-o', '--output', default='client', help='Output directory for generated files.')
    client_parser.add_argument(
        '-l', '--lang', default='csharp', help='Target client language (default: csharp).')
    client_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    client_parser.set_defaults(func=handle_client_command)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
