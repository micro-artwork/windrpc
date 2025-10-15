# proto/generator.py
import yaml
import os
import sys
from utils import spec_validator
from utils.loader import LineNumberLoader
from utils.converter import to_pascal_case
from utils.spec import merge_specs
from utils.file import copy, read_lines, write


def _get_template_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, f'templates/{file_name}')


def _get_service_commands(spec_data):
    cmd_dict = dict()
    services = spec_data.get('services', [])
    for service in services:
        svc_name = service['name']
        cmd_dict[svc_name] = []
        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == 'REQUEST_ONLY':
                resp = 'WINDRPC_WITHOUT_RESP'
            else:
                resp = 'WINDRPC_WITH_RESP'
            if rpc_type == 'NOTIFICATION':
                rpc_name = f"subscribe_{rpc_name}"
            cmd_dict[svc_name].append({
                'name': rpc_name,
                'resp': resp
            })
    return cmd_dict


def _generate_common_header_content(spec_data, package_name):
    file_path = _get_template_file_path('windrpc_common.h')
    cmd_dict = _get_service_commands(spec_data)
    header_paths = [
        f'#include "{package_name}/windrpc/core/windrpc.pb.h"\n',
        f'#include "{package_name}/windrpc/types/types.pb.h"\n'
    ]
    for svc_name in cmd_dict:
        header_paths.append(
            f'#include "{package_name}/windrpc/service/{svc_name}.pb.h"\n')

    content = []

    try:
        lines = read_lines(file_path)
        # 모든 라인을 순회
        for line in lines:
            if '--WINDRPC_PB_HEADERS' in line:
                content.append(line)
                content.extend(header_paths)
                content.append('\n')
            elif '--WINDRPC_PACKAGE_NAME' in line:
                content.append(line)
                content.append(
                    f"#define WINDRPC_PACKAGE_NAME {package_name}\n")
            elif '--WINDRPC_DECODE_SERVICE_FUNC' in line:
                content.append(line)
                content.append('#define WINDRPC_DECODE_SERVICE_FUNC \\\n')
                content.append('    WINDRPC_DECODE_FUNC(decode_service, \\\n')
                for svc_name in cmd_dict:
                    content.append(
                        f'   WINDRPC_DECODE_SERVICE_ENTRY({svc_name})  \\\n')
                content.append(')\n')
            elif '--WINDRPC_DECODE_COMMAND_FUNC_LIST' in line:
                content.append(line)
                content.append('#define WINDRPC_DECODE_COMMAND_FUNC_LIST \\\n')
                last_index = len(cmd_dict) - 1
                for index, (svc_name, value) in enumerate(cmd_dict.items()):
                    content.append(
                        f'   WINDRPC_DECODE_FUNC(decode_service_{svc_name}, \\\n')
                    if svc_name == 'common':
                        macro_name = 'WINDRPC_DECODE_COMMAND_ENTRY'
                    else:
                        macro_name = 'WINDRPC_DECODE_USER_COMMAND_ENTRY'
                    for cmd in value:
                        content.append(
                            f'    {macro_name}({svc_name}, {cmd['name']}, {cmd['resp']}) \\\n')
                    content.append(')')
                    if last_index != index:
                        content.append('\\\n')
            else:
                # 조건에 해당하지 않는 라인은 그대로 추가
                content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")
    content.append('\n')
    return "".join(content)


def _generate_windrpc_header_content(spec_data):
    file_path = _get_template_file_path('windrpc.h')
    services = spec_data.get('services', [])
    struct_content = []
    struct_windrpc_content = [
        'struct windrpc_user_service {'
    ]

    for index, service in enumerate(services):
        if index != 0:
            struct_content.append("};\n")

        name = service['name']
        struct_declare = f"struct windrpc_service_{name}"
        struct_content.append(f"{struct_declare} {{")

        if name != 'common':
            struct_windrpc_content.append(f"    {struct_declare} *{name};")

        for rpc in service.get('rpcs', []):
            rpc_type = rpc.get('type', '').upper()
            rpc_name = rpc['name']
            if rpc_type == "NOTIFICATION":
                struct_content.append(
                    f"    struct windrpc_procedure subscribe_{rpc_name};")
            else:
                struct_content.append(
                    f"    struct windrpc_procedure {rpc_name};")
    struct_content.append("};\n")
    struct_windrpc_content.extend([
        '};\n',
        'struct windrpc_service {',
        '   struct windrpc_service_common *common;',
        '   struct windrpc_user_service *user;',
        '};'])

    content = []
    try:
        lines = read_lines(file_path)
        for line in lines:
            if '--WINDRPC_STRUCTURES_FOR_SERVICE' in line:
                content.append(line)
                content.extend("\n".join(struct_content))
                content.extend("\n".join(struct_windrpc_content))
            else:
                content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")

    content.append('\n')
    return "".join(content)


def generate(core_spec_path, user_spec_path, output_dir, verbose=False):
    """
    주어진 YAML 스펙 파일들로부터 .proto와 .options 파일들을 생성합니다.
    """
    try:
        with open(core_spec_path, 'r', encoding='utf-8') as f:
            core_spec_data = yaml.load(f, Loader=LineNumberLoader)
    except FileNotFoundError:
        print(
            f"Error: Core spec file '{core_spec_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing core YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(user_spec_path, 'r', encoding='utf-8') as f:
            user_spec_data = yaml.load(f, Loader=LineNumberLoader)
    except FileNotFoundError:
        print(
            f"Error: User spec file '{user_spec_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing user YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    spec_data = merge_specs(core_spec_data, user_spec_data)
    spec_validator.validate(spec_data, verbose=verbose)
    print("YAML Specification validation successful.")

    package_name = spec_data.get('package', 'default_package')
    # output_path = os.path.join(output_dir, package_name)
    output_path = output_dir
    os.makedirs(output_path, exist_ok=True)

    print("\nGenerating WindRPC server files...")

    # generate windrpc_common.h
    common_header_content = _generate_common_header_content(
        spec_data, package_name)
    file_path = os.path.join(output_path, f"windrpc_common.h")
    write(file_path, common_header_content)
    print(f"Generated {file_path}")

    winrpc_header_content = _generate_windrpc_header_content(spec_data)
    file_path = os.path.join(output_path, f"windrpc.h")
    write(file_path, winrpc_header_content)
    print(f"Generated {file_path}")

    # copy windrpc_config.h
    file_path = os.path.join(output_dir, 'windrpc_config.h')
    if os.path.exists(file_path):
        print(f"'{file_path}' is already exist!")
    else:
        source_path = _get_template_file_path('windrpc_config.h')
        copy(source_path, file_path)

    # copy windrpc.c
    file_path = os.path.join(output_dir, 'windrpc.c')
    source_path = _get_template_file_path('windrpc.c')
    copy(source_path, file_path)
