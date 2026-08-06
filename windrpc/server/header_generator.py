import os
from utils.file import read_lines, copy


def get_template_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, f'templates/{file_name}')


def _get_proto_header_paths(spec_data, package_name):
    services = spec_data.get('services', [])
    proto_names = set()
    # 항상 생성되는 기본 proto 파일들
    proto_names.add("types")
    proto_names.add("windrpc")

    for service in services:
        if 'name' in service:
            proto_names.add(f"{service['name']}_service")

    header_paths = []
    for basename in sorted(list(proto_names)):
        # Nanopb는 'my_proto.proto' -> 'my_proto.pb.h' 파일을 생성합니다.
        header_path = os.path.join(package_name, f"{basename}.pb.h")
        # 윈도우와 리눅스 경로 구분자 통일을 위해'\'를 '/'로 변경
        header_paths.append(header_path.replace("\\", "/"))

    return header_paths


def generate_common_header_content(spec_data, package_name, verbose=False):
    file_path = get_template_file_path('windrpc_common.h')
    proto_header_paths = _get_proto_header_paths(spec_data, package_name)
    # print(proto_header_paths)
    content = []
    try:
        lines = read_lines(file_path)
        # 모든 라인을 순회
        for line in lines:
            if '--WINDRPC_PB_HEADERS' in line:
                # 마커 라인과 새로운 헤더 라인들을 순서대로 추가
                content.append(line)
                content.extend(
                    list(map(lambda path: f"#include \"{path}\"\n", proto_header_paths)))
            elif '--WINDRPC_PACKAGE_NAME' in line:
                # 새로운 패키지 이름 라인을 먼저 추가하고, 그 다음 마커 라인을 추가
                content.append(line)
                content.append(f"#define WINDRPC_PACKAGE_NAME {package_name}")
            else:
                # 조건에 해당하지 않는 라인은 그대로 추가
                content.append(line)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)

    return "".join(content)


def generate_config_header(output_dir):
    file_path = os.path.join(output_dir, 'windrpc_config.h')
    if os.path.exists(file_path):
        print(f"'{file_path}' is already exist!")
    else:
        source_path = get_template_file_path('windrpc_config.h')
        copy(source_path, file_path)


def generate_windrpc_header_content(spec_data, verbose=False):
    file_path = get_template_file_path('windrpc.h')
    content = []
    try:
        lines = read_lines(file_path)
        for line in lines:
            content.append(line)
    except FileNotFoundError:
        print(f"error: '{file_path}' is not found")

    return "".join(content)
