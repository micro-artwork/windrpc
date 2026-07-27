def normalize_rpc(rpc):
    """RPC 딕셔너리의 입력/출력 키 이름을 request/response 및 command/result 등으로 상호 정규화합니다."""
    if not isinstance(rpc, dict):
        return rpc

    # 입력(인자/요청) 필드 후보 탐색 (우선순위: request > command > params > parameter > input)
    req_val = None
    for key in ('request', 'command', 'params', 'parameter', 'input'):
        if key in rpc and rpc[key] is not None:
            req_val = rpc[key]
            break

    # 출력(결과/응답) 필드 후보 탐색 (우선순위: response > result > returns > return > output)
    res_val = None
    for key in ('response', 'result', 'returns', 'return', 'output'):
        if key in rpc and rpc[key] is not None:
            res_val = rpc[key]
            break

    if req_val is not None:
        rpc['request'] = req_val
        rpc['command'] = req_val  # 하위 호환성 유지

    if res_val is not None:
        rpc['response'] = res_val
        rpc['result'] = res_val  # 하위 호환성 유지

    return rpc


def merge_specs(core_spec, user_spec):
    """core_spec과 user_spec을 병합하여 하나의 스펙 딕셔너리를 만듭니다."""
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

    # 'types' 병합
    core_types = core_spec.get('types', {})
    user_types = user_spec.get('types', {})
    merged['types']['enums'].extend(core_types.get('enums', []))
    merged['types']['enums'].extend(user_types.get('enums', []))
    merged['types']['messages'].extend(core_types.get('messages', []))
    merged['types']['messages'].extend(user_types.get('messages', []))

    # 'services' 병합 및 RPC 키 정규화
    all_services = core_spec.get('services', []) + user_spec.get('services', [])
    for svc in all_services:
        svc_copy = dict(svc)
        if 'rpcs' in svc_copy and isinstance(svc_copy['rpcs'], list):
            svc_copy['rpcs'] = [normalize_rpc(rpc) for rpc in svc_copy['rpcs']]
        merged['services'].append(svc_copy)

    return merged


def combine_ids(service_id, rpc_id):
    """
    service_id를 상위 1바이트, rpc_id를 하위 1바이트로 조합하여
    하나의 16비트 정수를 만듭니다.
    """
    if not (0 <= service_id <= 0xFF and 0 <= rpc_id <= 0xFF):
        raise ValueError("ID values must be between 1 and 255.")

    combined_id = (service_id << 8) | rpc_id
    return combined_id

