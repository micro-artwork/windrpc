# utils/spec_validator.py
from utils.converter import to_pascal_case
import sys
import os

# 경로 설정을 통해 converter 모듈을 임포트
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


class ValidationError:
    """메시지, 컨텍스트, 줄 번호를 포함하는 유효성 검증 에러를 나타냅니다."""

    def __init__(self, message, context, line=None):
        self.message = message
        self.context = context
        self.line = line

    def __str__(self):
        line_info = f" (line ~{self.line})" if self.line else ""
        return f"{self.context}{line_info}: {self.message}"

    def __lt__(self, other):
        if self.line is not None and other.line is not None:
            if self.line != other.line:
                return self.line < other.line
        return str(self) < str(other)


def validate(spec_data, verbose=False):
    """전체 스펙에 대해 ID 고유성 및 기타 규칙을 검증합니다."""
    errors = []
    if verbose:
        print("--- Starting YAML Specification Validation ---")

    # --- 1. 사전 계산 ---
    PROTO_SCALAR_TYPES = {'double', 'float', 'int32', 'int64', 'uint32', 'uint64', 'sint32',
                          'sint64', 'fixed32', 'fixed64', 'sfixed32', 'sfixed64', 'bool', 'string', 'bytes'}
    package_name = spec_data.get('package')
    types_spec = spec_data.get('types', {})
    services = spec_data.get('services') or []
    VALID_RPC_TYPES = {'REQUEST_ONLY', 'REQUEST_RESPONSE', 'NOTIFICATION'}

    # 헬퍼 함수 정의 (to_pascal_case)
    def to_pascal_case(name):
        """스네이크 케이스나 카멜 케이스를 파스칼 케이스로 변환합니다."""
        if not name or not isinstance(name, str):
            return name
        if '_' in name:
            return "".join(word.capitalize() for word in name.split('_'))
        else:
            return name[0].upper() + name[1:]

    # 교차 파일 검증을 위한 이름 목록 사전 계산
    normalized_service_names = {to_pascal_case(
        svc.get('name')) for svc in services if svc.get('name')}

    common_messages = {msg.get('name')
                       for msg in (types_spec.get('messages') or [])}
    common_enums = {enum.get('name')
                    for enum in (types_spec.get('enums') or [])}

    service_types = {
        svc.get('name'): {
            'messages': {msg.get('name') for msg in (svc.get('messages') or [])},
            'enums': {enum.get('name') for enum in (svc.get('enums') or [])}
        } for svc in services
    }

    # --- 2. 헬퍼 함수 ---
    # --- 2. [수정됨] 유효성 검증 헬퍼 함수 ---
    def is_valid_type(type_name, current_service_name=None):
        if not type_name or not isinstance(type_name, str):
            return False
        if type_name.lower() in PROTO_SCALAR_TYPES:
            return True

        parts = type_name.split('.')

        # Case A: 전체 경로 (e.g., hlt.types.Empty)
        if len(parts) == 3 and parts[0] == package_name and parts[1] == 'types':
            return to_pascal_case(parts[2]) in common_messages or to_pascal_case(parts[2]) in common_enums

        # Case B: 부분 경로 (e.g., types.Empty)
        if len(parts) == 2 and parts[0] == 'types':
            return to_pascal_case(parts[1]) in common_messages or to_pascal_case(parts[1]) in common_enums

        # Case C: 다른 서비스의 타입 (e.g., power.PowerInfo)
        if len(parts) == 2:
            svc_name, msg_name = parts
            if svc_name in service_types and to_pascal_case(msg_name) in (service_types[svc_name]['messages'] | service_types[svc_name]['enums']):
                return True

        # Case D: 이름만 주어진 경우 (e.g., Empty or PixelData)
        if len(parts) == 1:
            pascal_type = to_pascal_case(parts[0])
            # D-1: 현재 서비스 내 타입
            if current_service_name and pascal_type in (service_types[current_service_name]['messages'] | service_types[current_service_name]['enums']):
                return True
            # D-2: 공용 타입
            if pascal_type in common_messages or pascal_type in common_enums:
                return True

        return False

    def check_uniqueness(items, key, context_name):
        seen_values = set()
        if not items:
            return
        for item in items:
            value = item.get(key)
            if value is None:
                continue
            if value in seen_values:
                errors.append(ValidationError(
                    f"Duplicate value '{value}' for key '{key}'.", f"{context_name} -> item '{item.get('name', 'N/A')}'", item.get('__line__')))
            seen_values.add(value)

    def check_normalized_name_uniqueness(items, key, context_name, normalizer):
        """정규화된 이름의 고유성을 확인합니다. (범위 내에서)"""
        seen_normalized_names = {}  # {normalized_name: first_item}
        if not items:
            return
        for item in items:
            original_name = item.get(key)
            if original_name is None:
                continue

            normalized_name = normalizer(original_name)

            if normalized_name in seen_normalized_names:
                first_item = seen_normalized_names[normalized_name]
                first_item_name = first_item.get(key)
                error_msg = (f"Effective duplicate name '{original_name}'. "
                             f"It normalizes to '{normalized_name}', which conflicts with '{first_item_name}' (line ~{first_item.get('__line__')}) within the same scope.")
                errors.append(ValidationError(
                    error_msg, context_name, item.get('__line__')))
            else:
                seen_normalized_names[normalized_name] = item

    def validate_fields(msg_def, context_name, current_service_name):
        all_fields = list(msg_def.get('fields') or [])
        for oneof in (msg_def.get('oneofs') or []):
            all_fields.extend(oneof.get('fields') or [])

        check_uniqueness(all_fields, 'number', context_name)
        check_uniqueness(all_fields, 'name', context_name)

        for field in all_fields:
            if not is_valid_type(field.get('type'), current_service_name):
                errors.append(ValidationError(
                    f"Invalid type '{field.get('type')}' for field '{field.get('name')}'.", context_name, field.get('__line__')))

    # 수정된 enum 검증 헬퍼 함수
    def validate_enums(enum_defs, context_base_name):
        for enum_def in enum_defs:
            enum_name = enum_def.get('name', 'N/A')
            enum_context = f"{context_base_name} -> enum '{enum_name}'"
            enum_members = enum_def.get('members') or []

            # 'name' 고유성 검사는 그대로 유지 (enum 멤버 이름은 고유해야 함)
            check_uniqueness(enum_members, 'name',
                             f"{enum_context} -> members")

            seen_explicit_values = set()
            has_zero = False
            first_member_has_value_0 = False

            # YAML 로더가 줄 번호를 주입하는 방식이므로, members 리스트에서 첫 번째 멤버를 안전하게 확인
            first_member = enum_members[0] if enum_members else None

            # 0 값 존재 여부 검사
            # Case 1: 첫 번째 멤버의 value가 0으로 명시된 경우
            if first_member and first_member.get('value') == 0:
                has_zero = True
                first_member_has_value_0 = True
            # Case 2: 첫 번째 멤버에 value가 없어서 자동으로 0이 할당될 경우
            elif first_member and 'value' not in first_member:
                has_zero = True
                first_member_has_value_0 = True
            # Case 3: 다른 멤버에 0이 명시적으로 존재하는 경우
            else:
                for member in enum_members:
                    if member.get('value') == 0:
                        has_zero = True
                        break

            if not has_zero:
                errors.append(ValidationError(
                    "Enum must contain a member with value 0. Protocol Buffer 3 requires the first enum value to be 0 or to be implicitly assigned 0.", enum_context, enum_def.get('__line__')))

            # 중복 값 검사 (명시적으로 지정된 값만 검사)
            for i, member in enumerate(enum_members):
                member_name = member.get('name', 'N/A')
                line = member.get('__line__')

                # 'value'가 명시적으로 정의된 경우에만 중복을 검사
                if 'value' in member:
                    member_value = member.get('value')

                    # Protocol Buffer 3에서 첫 번째 enum 값은 0이어야 함 (명시적 또는 암묵적)
                    # 만약 첫 번째 멤버가 아닌데 value=0을 명시하면 중복으로 간주
                    # 또는 첫 번째 멤버라도 value=0이 아닌 값을 명시하면 오류
                    if i == 0 and member_value != 0:
                        errors.append(ValidationError(
                            f"The first enum member '{member_name}' must have a value of 0. Received: {member_value}", enum_context, line))

                    if member_value in seen_explicit_values:
                        errors.append(ValidationError(
                            f"Duplicate explicit value '{member_value}' for enum member '{member_name}'.", enum_context, line))
                    seen_explicit_values.add(member_value)
                else:
                    # 'value'가 없는 멤버에 대해, 이전 멤버에 'value'가 없었다면 0이 할당될 것이므로
                    # 이전에 'value'가 없는 첫 번째 멤버가 이미 0을 가졌는지 확인
                    if i == 0 and not has_zero:  # 이 조건은 위에서 처리되므로 사실상 필요 없음.
                        # 하지만 혹시 모르니 남겨둠.
                        errors.append(ValidationError(
                            f"The first enum member '{member_name}' must implicitly or explicitly have a value of 0.", enum_context, line))

                    # 'value'가 명시되지 않은 경우, generate_protos.py가 순차적으로 값을 할당할 것이므로
                    # 이 단계에서 충돌을 미리 감지할 필요는 없음. (generate_protos.py가 유효한 값을 부여할 것임)
                    pass

    # --- 3. 메인 검증 로직 ---

    if verbose:
        print("Validating cross-file package and name safety...")

    check_normalized_name_uniqueness(
        services, 'name', 'services list', to_pascal_case)

    if 'Types' in normalized_service_names:
        for svc in services:
            if to_pascal_case(svc.get('name')) == 'Types':
                errors.append(ValidationError("Service name 'types' is reserved for common types.",
                              f"service '{svc.get('name')}'", svc.get('__line__')))
                break

    all_definitions = (types_spec.get('messages') or []) + \
        (types_spec.get('enums') or [])
    for item in all_definitions:
        normalized_item_name = to_pascal_case(item.get('name'))
        if normalized_item_name in normalized_service_names:
            item_type = 'Message' if 'fields' in item else 'Enum'
            errors.append(ValidationError(
                f"{item_type} name '{item.get('name')}' in 'types' conflicts with a service name after normalization to '{normalized_item_name}'.",
                "types", item.get('__line__')))

    for svc in services:
        for item in ((svc.get('messages') or []) + (svc.get('enums') or [])):
            normalized_item_name = to_pascal_case(item.get('name'))
            if normalized_item_name in normalized_service_names:
                item_type = 'Message' if 'fields' in item else 'Enum'
                errors.append(ValidationError(
                    f"{item_type} name '{item.get('name')}' conflicts with a service name after normalization to '{normalized_item_name}'.",
                    f"service '{svc.get('name')}'", svc.get('__line__')))

    if verbose:
        print("Validating 'types' section for internal uniqueness...")
    types_messages = types_spec.get('messages') or []
    types_enums = types_spec.get('enums') or []

    check_uniqueness(types_messages, 'name', "types.messages")
    check_normalized_name_uniqueness(
        types_messages, 'name', "types.messages", to_pascal_case)
    check_uniqueness(types_enums, 'name', "types.enums")
    check_normalized_name_uniqueness(
        types_enums, 'name', "types.enums", to_pascal_case)

    for msg_def in types_messages:
        validate_fields(
            msg_def, f"types.message '{msg_def.get('name')}'", None)

    # Enum 검증 로직 추가
    validate_enums(types_enums, "types")

    if not services:
        errors.append(ValidationError(
            "At least one service must be defined.", "services"))
    check_uniqueness(services, 'id', "services list")
    check_uniqueness(services, 'name', "services list")

    for svc in services:
        svc_name = svc.get('name', 'N/A')
        svc_context = f"service '{svc_name}'"
        if verbose:
            print(f"Validating {svc_context} for internal uniqueness...")

        service_messages = svc.get('messages') or []
        service_enums = svc.get('enums') or []
        rpcs = svc.get('rpcs') or []

        check_uniqueness(service_messages, 'name',
                         f"{svc_context} -> messages")
        check_normalized_name_uniqueness(
            service_messages, 'name', f"{svc_context} -> messages", to_pascal_case)
        check_uniqueness(service_enums, 'name', f"{svc_context} -> enums")
        check_normalized_name_uniqueness(
            service_enums, 'name', f"{svc_context} -> enums", to_pascal_case)

        for msg_def in service_messages:
            validate_fields(
                msg_def, f"{svc_context} -> message '{msg_def.get('name')}'", svc_name)

        # 서비스 내 enum 검증 로직 추가
        validate_enums(service_enums, svc_context)

        check_uniqueness(rpcs, 'id', f"{svc_context} -> rpcs")
        check_uniqueness(rpcs, 'name', f"{svc_context} -> rpcs")

        for op in rpcs:
            op_context = f"{svc_context} -> rpc '{op.get('name')}'"
            type = op.get('type', '').upper()
            line = op.get('__line__')

            if type not in VALID_RPC_TYPES:
                errors.append(ValidationError(
                    f"Invalid 'type' value '{op.get('type')}'. Must be one of {VALID_RPC_TYPES}.", op_context, line))
                continue

            if type == 'REQUEST_ONLY':
                if 'command' not in op:
                    errors.append(ValidationError(
                        "'command' key is required for REQUEST_ONLY.", op_context, line))
                elif not is_valid_type(op['command'], svc_name):
                    errors.append(ValidationError(
                        f"Invalid type for 'command': {op['command']}", op_context, line))

            elif type == 'REQUEST_RESPONSE':
                if 'command' not in op:
                    errors.append(ValidationError(
                        "'command' key is required for REQUEST_RESPONSE.", op_context, line))
                elif not is_valid_type(op['command'], svc_name):
                    errors.append(ValidationError(
                        f"Invalid type for 'command': {op['command']}", op_context, line))
                if 'result' not in op:
                    errors.append(ValidationError(
                        "'result' key is required for REQUEST_RESPONSE.", op_context, line))
                elif not is_valid_type(op['result'], svc_name):
                    errors.append(ValidationError(
                        f"Invalid type for 'result': {op['result']}", op_context, line))

            elif type == 'NOTIFICATION':
                if 'event' not in op:
                    errors.append(ValidationError(
                        "'event' key is required for NOTIFICATION.", op_context, line))
                elif not is_valid_type(op['event'], svc_name):
                    errors.append(ValidationError(
                        f"Invalid type for 'event': {op['event']}", op_context, line))

    # --- 4. 에러 보고 ---
    if errors:
        print("\nYAML Specification Validation Failed:")
        for error in sorted(errors):
            print(f"- {error}")
        sys.exit(1)
    elif verbose:
        print("\n--- Validation finished successfully. ---")
