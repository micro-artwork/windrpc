# windrpc/client/generator.py
import os
import sys
import yaml
import glob

from utils.loader import LineNumberLoader
from utils.spec import merge_specs
from utils import spec_validator
from utils.protoc_resolver import ProtocResolver
from proto import generator as proto_generator
from .csharp import generate_csharp_client
from .js import generate_js_client, generate_cobs_js
from .python import generate_python_client


def generate(core_spec_path, user_spec_path, output_dir, lang="csharp", verbose=False, compile_proto=True):
    """
    Generates client SDK source code (C# / JavaScript / Python / etc.) based on YAML specification.
    Includes automatic .proto generation and protoc data class compilation.
    """
    try:
        with open(core_spec_path, 'r', encoding='utf-8') as f:
            core_spec_data = yaml.load(f, Loader=LineNumberLoader)
        with open(user_spec_path, 'r', encoding='utf-8') as f:
            user_spec_data = yaml.load(f, Loader=LineNumberLoader)
    except FileNotFoundError as e:
        print(f"Error: Spec file not found - {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    spec_data = merge_specs(core_spec_data, user_spec_data)
    spec_validator.validate(spec_data, verbose=verbose)

    package_name = spec_data.get('package', 'default_package')
    os.makedirs(output_dir, exist_ok=True)

    lang_lower = lang.lower().replace('#', 'sharp')

    if lang_lower in ('csharp', 'cs', 'c_sharp'):
        print(f"\n--- Starting One-Stop C# Client Generation for package '{package_name}' ---")

        # Step 1: Generate .proto files under Protos subfolder
        protos_dir = os.path.join(output_dir, "Protos")
        os.makedirs(protos_dir, exist_ok=True)
        print(f"[Step 1/3] Generating .proto files into '{protos_dir}'...")
        proto_generator.generate(
            core_spec_path=core_spec_path,
            user_spec_path=user_spec_path,
            output_dir=protos_dir,
            verbose=verbose
        )

        # Step 2: Resolve protoc & compile .proto to C# Data Classes in Generated subfolder
        if compile_proto:
            gen_csharp_dir = os.path.join(output_dir, "Generated")
            os.makedirs(gen_csharp_dir, exist_ok=True)
            print(f"[Step 2/3] Resolving protoc and compiling .proto to C# Classes into '{gen_csharp_dir}'...")
            proto_files = glob.glob(os.path.join(protos_dir, "**", "*.proto"), recursive=True)
            if not proto_files:
                print("Error: No .proto files found to compile.", file=sys.stderr)
                sys.exit(1)

            ProtocResolver.compile(
                proto_files=proto_files,
                proto_imports=[protos_dir],
                out_dir=gen_csharp_dir,
                lang="csharp"
            )
        else:
            print("[Step 2/3] Skipping protoc execution (compile_proto=False)")

        # Step 3: Generate WindRpcClient.cs SDK
        print(f"[Step 3/3] Generating WindRpcClient.cs Client SDK...")
        csharp_code = generate_csharp_client(spec_data, package_name)
        out_file = os.path.join(output_dir, "WindRpcClient.cs")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(csharp_code)
        print(f"Generated {out_file}")
        print(f"--- C# Client SDK & Data Classes Generation Complete ---")

    elif lang_lower in ('js', 'javascript', 'ts', 'typescript'):
        print(f"\n--- Starting JavaScript/TypeScript Client Generation for package '{package_name}' ---")

        # Step 1 (optional): Generate .proto files for documentation/reference
        if compile_proto:
            protos_dir = os.path.join(output_dir, "Protos")
            os.makedirs(protos_dir, exist_ok=True)
            print(f"[Step 1/2] Generating reference .proto files into '{protos_dir}'...")
            proto_generator.generate(
                core_spec_path=core_spec_path,
                user_spec_path=user_spec_path,
                output_dir=protos_dir,
                verbose=verbose
            )
        else:
            print("[Step 1/2] Skipping .proto generation (compile_proto=False)")

        # Step 2: Generate WindRpcClient.js SDK (no external proto dependency)
        print(f"[Step 2/2] Generating WindRpcClient.js SDK (inline Protobuf encoding & COBS)...")
        js_code = generate_js_client(spec_data, package_name)
        client_file = os.path.join(output_dir, "WindRpcClient.js")
        with open(client_file, 'w', encoding='utf-8') as f:
            f.write(js_code)

        print(f"Generated {client_file}")
        print(f"--- JS/TS Client SDK Generation Complete (no external dependencies) ---")

    elif lang_lower in ('python', 'py'):
        print(f"\n--- Starting One-Stop Python Client Generation for package '{package_name}' ---")

        # Step 1: Generate .proto files under Protos subfolder
        protos_dir = os.path.join(output_dir, "Protos")
        os.makedirs(protos_dir, exist_ok=True)
        print(f"[Step 1/3] Generating .proto files into '{protos_dir}'...")
        proto_generator.generate(
            core_spec_path=core_spec_path,
            user_spec_path=user_spec_path,
            output_dir=protos_dir,
            verbose=verbose
        )

        # Step 2: Compile .proto to Python modules using protoc
        if compile_proto:
            gen_py_dir = os.path.join(output_dir, "Generated")
            os.makedirs(gen_py_dir, exist_ok=True)
            print(f"[Step 2/3] Resolving protoc and compiling .proto to Python modules into '{gen_py_dir}'...")
            proto_files = glob.glob(os.path.join(protos_dir, "**", "*.proto"), recursive=True)
            if not proto_files:
                print("Error: No .proto files found to compile.", file=sys.stderr)
                sys.exit(1)

            ProtocResolver.compile(
                proto_files=proto_files,
                proto_imports=[protos_dir],
                out_dir=gen_py_dir,
                lang="python"
            )

            # Create empty __init__.py files for clean Python module imports
            for root, dirs, files in os.walk(gen_py_dir):
                init_file = os.path.join(root, "__init__.py")
                if not os.path.exists(init_file):
                    open(init_file, 'a').close()
        else:
            print("[Step 2/3] Skipping protoc execution (compile_proto=False)")

        # Step 3: Generate WindRpcClient.py SDK
        print(f"[Step 3/3] Generating WindRpcClient.py Client SDK...")
        py_code = generate_python_client(spec_data, package_name)
        out_file = os.path.join(output_dir, "WindRpcClient.py")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(py_code)
        print(f"Generated {out_file}")
        print(f"--- Python Client SDK & Data Classes Generation Complete ---")

    else:
        print(f"Error: Unsupported client language '{lang}'. Supported: 'csharp', 'js', 'ts', 'python'", file=sys.stderr)
        sys.exit(1)
