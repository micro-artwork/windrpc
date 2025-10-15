# --- [신규] 스펙 병합 함수 ---
def merge_specs(core_spec, user_spec):
    """core_spec과 user_spec을 병합하여 하나의 스펙 딕셔너리를 만듭니다."""
    # 깊은 복사를 위해 새로운 딕셔너리에서 시작
    merged = {
        'platform_version_code': user_spec.get('platform_version_code', core_spec.get('platform_version_code')),
        'package': user_spec.get('package', core_spec.get('package')),
        'config': user_spec.get('config', {}),
        'types': {
            'enums': [],
            'messages': []
        },
        'services': []
    }

    # 'types' 병합: core와 user의 enums와 messages 리스트를 합칩니다.
    core_types = core_spec.get('types', {})
    user_types = user_spec.get('types', {})
    merged['types']['enums'].extend(core_types.get('enums', []))
    merged['types']['enums'].extend(user_types.get('enums', []))
    merged['types']['messages'].extend(core_types.get('messages', []))
    merged['types']['messages'].extend(user_types.get('messages', []))

    # 'services' 병합: core와 user의 services 리스트를 합칩니다.
    merged['services'].extend(core_spec.get('services', []))
    merged['services'].extend(user_spec.get('services', []))

    return merged


def combine_ids(service_id, rpc_id):
    """
    service_id를 상위 1바이트, rpc_id를 하위 1바이트로 조합하여
    하나의 16비트 정수를 만듭니다.

    Args:
        service_id (int): 서비스 ID (6 ~ 255).
        rpc_id (int): RPC ID (1 ~ 255).

    Returns:
        int: combined 16bit id
    """
    # ID가 16비트 범위를 초과하는지 확인 (선택 사항)
    if not (0 <= service_id <= 0xFF and 0 <= rpc_id <= 0xFF):
        raise ValueError("ID values ​​must be between 1 and 255.")

    combined_id = (service_id << 8) | rpc_id
    return combined_id
