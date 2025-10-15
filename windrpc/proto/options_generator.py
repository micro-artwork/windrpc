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

    options_by_file = collections.defaultdict(list)

    def _collect_options(item, current_service_name, current_msg_name=None):
        """재귀적으로 'nanopb' 옵션을 수집하는 헬퍼 함수입니다."""
        if 'nanopb' in item:
            # 대상 이름 구성 (예: hlt.power.PowerInfo.voltage_mill)
            name_parts = [f"{package_prefix}.windrpc"]
            if current_service_name == "types":
                name_parts.extend([f"{current_service_name}"])
            else:
                name_parts.extend([f"service.{current_service_name}"])

            if current_msg_name:
                name_parts.append(current_msg_name)
            name_parts.append(item['name'])
            target_name = ".".join(name_parts)

            for key, value in item['nanopb'].items():
                if key == '__line__':
                    continue
                formatted_value = _format_nanopb_option_value(value)
                line = f"{target_name} {key}: {formatted_value}"

                # 'types' 서비스의 옵션은 types.options 파일에 저장하고, 나머지는 각 서비스 파일에 저장합니다.
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

        # 각 서비스의 Request, Response, Notification 메시지에 콜백 옵션 자동 추가
        # oneof 필드를 포함하는 메시지는 Nanopb에서 콜백 처리가 필요합니다.
        if service_spec.get('rpcs'):
            full_service_package = f"{package_prefix}.windrpc.service.{svc_name}"
            # v2 구조에서는 Request, Response, Notification 메시지가 항상 생성될 수 있으므로
            # 해당 메시지에 대한 콜백 옵션을 기본으로 추가해주는 것이 안전합니다.
            rpcs = service_spec.get('rpcs') or []
            request_exist = False
            response_exist = False
            notification_exist = False

            for op in rpcs:
                type = op.get('type', '').upper()
                if type == 'NOTIFICATION':
                    request_exist = True
                    response_exist = True
                    notification_exist = True
                    break
                elif type == 'REQUEST_RESPONSE':
                    request_exist = True
                    response_exist = True
                elif type == 'REQUEST_ONLY':
                    request_exist = True

            if request_exist:
                options_by_file[svc_name].append(
                    f"{full_service_package}.Request submsg_callback: true")
            if response_exist:
                options_by_file[svc_name].append(
                    f"{full_service_package}.Response submsg_callback: true")
            if notification_exist:
                options_by_file[svc_name].append(
                    f"{full_service_package}.Notification submsg_callback: true")

    # --- [추가] 3. windrpc.proto 옵션 추가 ---
    windrpc_package = f"{package_prefix}.windrpc.core"
    windrpc_messages = ["ClientMessage", "ServerMessage",
                        "Request", "Response", "Notification"]
    for msg_name in windrpc_messages:
        options_by_file['windrpc'].append(
            f"{windrpc_package}.{msg_name} submsg_callback: true")
        if msg_name in ["Request", "Response"]:
            options_by_file['windrpc'].append(
                f"{windrpc_package}.{msg_name}.request_id max_length: 37")

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
