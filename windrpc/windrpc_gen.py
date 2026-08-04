# windrpc_gen.py

import argparse
import sys
import os
from proto import generator as proto_generator
from server import generator as server_generator
from client import generator as client_generator


def _resolve_paths(args):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    # Core Spec Path
    if args.core_spec:
        if os.path.isabs(args.core_spec):
            core_spec_path = args.core_spec
        elif os.path.exists(os.path.join(cwd, args.core_spec)):
            core_spec_path = os.path.abspath(os.path.join(cwd, args.core_spec))
        else:
            core_spec_path = os.path.join(script_dir, args.core_spec)
    else:
        local_core = os.path.join(cwd, 'core_spec.yml')
        if os.path.exists(local_core):
            core_spec_path = local_core
        else:
            core_spec_path = os.path.join(script_dir, 'core_spec.yml')

    # User Spec Path
    if os.path.isabs(args.user_spec):
        user_spec_path = args.user_spec
    else:
        user_spec_path = os.path.abspath(os.path.join(cwd, args.user_spec))

    # Output Dir
    if os.path.isabs(args.output):
        output_dir = args.output
    else:
        output_dir = os.path.abspath(os.path.join(cwd, args.output))

    return core_spec_path, user_spec_path, output_dir


def handle_proto_command(args):
    """Handles the 'proto' subcommand."""
    print("--- Starting Protobuf Generation ---")
    core_spec_path, user_spec_path, output_dir = _resolve_paths(args)

    proto_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        mode=args.mode,
        verbose=args.verbose,
        strict=args.strict
    )
    print("--- Protobuf Generation Finished ---")


def handle_server_command(args):
    """Handles the 'server' subcommand."""
    print("--- Starting RPC Server Generation ---")
    core_spec_path, user_spec_path, output_dir = _resolve_paths(args)

    server_generator.generate(
        core_spec_path=core_spec_path,
        user_spec_path=user_spec_path,
        output_dir=output_dir,
        mode=args.mode,
        rtos=args.rtos,
        verbose=args.verbose)
    print("--- RPC Server Generation Finished ---")


def handle_client_command(args):
    """Handles the 'client' subcommand."""
    print(f"--- Starting RPC Client Generation ({args.lang}) ---")
    core_spec_path, user_spec_path, output_dir = _resolve_paths(args)

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

    # --- Define 'proto' subcommand ---
    proto_parser = subparsers.add_parser(
        'proto', help='Generate .proto files from YAML specifications.')
    proto_parser.add_argument(
        '-c', '--core-spec', default=None, help='Input core YAML spec file (optional, defaults to built-in core_spec.yml).')
    proto_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    proto_parser.add_argument(
        '-o', '--output', default='protos', help='Output directory for generated files.')
    proto_parser.add_argument(
        '-m', '--mode', choices=['nested', 'flat'], default=None, help='Envelope mode: flat (default) or nested.')
    proto_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    proto_parser.add_argument(
        '--strict', action='store_true',
        help='Strict proto style enforcement: treat missing enum value prefixes as errors instead of auto-fixing.')
    proto_parser.set_defaults(func=handle_proto_command)

    # --- Define 'server' subcommand ---
    server_parser = subparsers.add_parser(
        'server', help='Generate RPC server C code.')
    server_parser.add_argument(
        '-c', '--core-spec', default=None, help='Input core YAML spec file (optional, defaults to built-in core_spec.yml).')
    server_parser.add_argument(
        '-s', '--user-spec', default='user_spec.yml', help='Input user-defined YAML spec file.')
    server_parser.add_argument(
        '-o', '--output', default='server', help='Output directory for generated files.')
    server_parser.add_argument(
        '-m', '--mode', choices=['nested', 'flat'], default=None, help='Envelope mode: flat (default) or nested.')
    server_parser.add_argument(
        '-r', '--rtos', choices=['zephyr', 'none'], default='zephyr', help='Target RTOS (default: zephyr).')
    server_parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose output.')
    server_parser.set_defaults(func=handle_server_command)

    # --- Define 'client' subcommand ---
    client_parser = subparsers.add_parser(
        'client', help='Generate RPC client SDK code (e.g. C#).')
    client_parser.add_argument(
        '-c', '--core-spec', default=None, help='Input core YAML spec file (optional, defaults to built-in core_spec.yml).')
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
