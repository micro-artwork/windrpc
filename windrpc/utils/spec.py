def normalize_rpc(rpc):
    """Normalizes RPC dictionary input/output field keys across request/response and command/result."""
    if not isinstance(rpc, dict):
        return rpc

    # Search candidates for request/input field (priority: request > command > params > parameter > input)
    req_val = None
    for key in ('request', 'command', 'params', 'parameter', 'input'):
        if key in rpc and rpc[key] is not None:
            req_val = rpc[key]
            break

    # Search candidates for response/output field (priority: response > result > returns > return > output)
    res_val = None
    for key in ('response', 'result', 'returns', 'return', 'output'):
        if key in rpc and rpc[key] is not None:
            res_val = rpc[key]
            break

    if req_val is not None:
        rpc['request'] = req_val
        rpc['command'] = req_val  # Maintain backward compatibility

    if res_val is not None:
        rpc['response'] = res_val
        rpc['result'] = res_val  # Maintain backward compatibility

    return rpc


def merge_specs(core_spec, user_spec):
    """Merges core_spec and user_spec into a single unified specification dictionary."""
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

    # Merge 'types'
    core_types = core_spec.get('types', {})
    user_types = user_spec.get('types', {})
    merged['types']['enums'].extend(core_types.get('enums', []))
    merged['types']['enums'].extend(user_types.get('enums', []))
    merged['types']['messages'].extend(core_types.get('messages', []))
    merged['types']['messages'].extend(user_types.get('messages', []))

    # Merge 'services' and normalize RPC keys
    all_services = core_spec.get('services', []) + user_spec.get('services', [])
    for svc in all_services:
        svc_copy = dict(svc)
        if 'rpcs' in svc_copy and isinstance(svc_copy['rpcs'], list):
            svc_copy['rpcs'] = [normalize_rpc(rpc) for rpc in svc_copy['rpcs']]
        merged['services'].append(svc_copy)

    return merged


def combine_ids(service_id, rpc_id):
    """
    Combines service_id (high byte) and rpc_id (low byte) into a 16-bit integer.
    """
    if not (0 <= service_id <= 0xFF and 0 <= rpc_id <= 0xFF):
        raise ValueError("ID values must be between 1 and 255.")

    combined_id = (service_id << 8) | rpc_id
    return combined_id

