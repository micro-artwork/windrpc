# options_generator.py
import os
import collections


def _format_nanopb_option_value(value):
    """Nanopb 옵션 값을 .options 파일 형식에 맞게 포맷팅합니다."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        # FT_CALLBACK 등 Nanopb의 알려진 enum 값은 따옴표로 묶지 않습니다.
        if value.startswith(('FT_', 'IS_', 'M_', 'DS_')):
            return value
        return f'"{value}"'
    # 정수 값
    return str(value)


def generate_options_files(spec_data, output_dir, package_prefix, verbose=False):
    """
    YAML 사양 데이터에서 'nanopb' 키를 추출하여 .options 파일을 생성합니다.
    """
    if verbose:
        print("--- Starting Nanopb Options Extraction ---")

    config = spec_data.get('config', {})
    default_str_max = config.get('default_string_max_size', 64)
    default_bytes_max = config.get('default_bytes_max_size', 64)
    default_array_max = config.get('default_array_max_count', 16)

    options_by_file = collections.defaultdict(list)

    def _collect_options(item, current_service_name, current_msg_name=None):
        """재귀적으로 'nanopb' 옵션을 수집하는 헬퍼 함수입니다."""
        item_nanopb = item.get('nanopb', {})

        # string / bytes / repeated 필드에 대한 기본 max_size / max_count 자동 부여
        f_type = item.get('type')
        f_prop = item.get('property')

        if f_type == 'string' and 'max_size' not in item_nanopb and 'max_length' not in item_nanopb:
            item_nanopb['max_size'] = default_str_max
        elif f_type == 'bytes' and 'max_size' not in item_nanopb and 'max_length' not in item_nanopb:
            item_nanopb['max_size'] = default_bytes_max

        if f_prop == 'repeated' and 'max_count' not in item_nanopb:
            item_nanopb['max_count'] = default_array_max

        if item_nanopb:
            name_parts = [f"{package_prefix}.windrpc"]
            if current_service_name == "types":
                name_parts.extend([f"{current_service_name}"])
            else:
                name_parts.extend([f"service.{current_service_name}"])

            if current_msg_name:
                name_parts.append(current_msg_name)
            name_parts.append(item['name'])
            target_name = ".".join(name_parts)

            for key, value in item_nanopb.items():
                if key == '__line__':
                    continue
                formatted_value = _format_nanopb_option_value(value)
                line = f"{target_name} {key}: {formatted_value}"

                file_key = 'types' if current_service_name == 'types' else current_service_name
                options_by_file[file_key].append(line)

    # --- 1. 'types' 섹션 처리 ---
    types_spec = spec_data.get('types', {})
    for msg_def in types_spec.get('messages', []):
        for field in msg_def.get('fields', []):
            _collect_options(field, 'types', msg_def['name'])

    # --- 2. 'services' 섹션 처리 ---
    for service_spec in spec_data.get('services', []):
        svc_name = service_spec['name']

        # 서비스 내 메시지 필드 옵션
        for msg_def in service_spec.get('messages', []):
            for field in msg_def.get('fields', []):
                _collect_options(field, svc_name, msg_def['name'])
            for oneof in msg_def.get('oneofs', []):
                for field in oneof.get('fields', []):
                    _collect_options(field, svc_name, msg_def['name'])

    # --- 3. windrpc.proto 옵션 추가 ---
    envelope_mode = config.get('envelope_mode', 'flat')
    if envelope_mode != 'flat':
        windrpc_package = f"{package_prefix}.windrpc.core"
        options_by_file['windrpc'].append(
            f"{windrpc_package}.Request.request_id max_size: 38")
        options_by_file['windrpc'].append(
            f"{windrpc_package}.Response.request_id max_size: 38")

    # --- 4. 파일 쓰기 ---
    for file_key, options_list in options_by_file.items():
        # 파일 이름 결정 로직 수정
        if file_key == 'types':
            options_file_name = 'types/types.options'
        elif file_key == 'windrpc':
            options_file_name = 'core/windrpc.options'
        else:  # 서비스 파일인 경우
            options_file_name = f"service/{file_key}.options"

        options_file_path = os.path.join(output_dir, options_file_name)

        with open(options_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Nanopb options for {file_key}\n")
            for line in sorted(list(set(options_list))):  # 중복 제거 및 정렬
                f.write(line + "\n")

        if verbose:
            print(f"  - Generated options file: {options_file_path}")

    if verbose:
        print("--- Nanopb Options Extraction Finished ---")
