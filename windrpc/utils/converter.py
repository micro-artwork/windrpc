import re


def to_pascal_case(snake_str):
    """snake_case 또는 camelCase 문자열을 PascalCase로 변환합니다."""
    if not snake_str or not isinstance(snake_str, str):
        return ""
    if '_' in snake_str:
        return "".join(word.capitalize() for word in snake_str.split('_'))
    return snake_str[0].upper() + snake_str[1:]


def to_upper_snake_case(name):
    """PascalCase 또는 camelCase 문자열을 UPPER_SNAKE_CASE로 변환합니다.
    예: 'PowerMode' → 'POWER_MODE', 'StatusCode' → 'STATUS_CODE'
    """
    if not name or not isinstance(name, str):
        return ""
    # 연속 대문자(약어) 처리: 'HTTPStatus' → 'HTTP_Status' 로 먼저 변환
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    # 소문자→대문자 경계에 언더스코어 삽입
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.upper()


def enum_value_prefix(enum_name, explicit_prefix=None):
    """Proto 스타일 가이드에 따른 enum 값 접두어를 반환합니다.

    explicit_prefix가 지정되면 그것을 사용하고, 없으면 enum 타입명에서 자동 계산합니다.
    예: enum_name='PowerMode' → 'POWER_MODE_'
        enum_name='StatusCode', explicit_prefix='SC' → 'SC_'
    """
    if explicit_prefix:
        prefix = explicit_prefix.rstrip('_').upper()
    else:
        prefix = to_upper_snake_case(enum_name)
    return prefix + '_'


def apply_enum_prefix(member_name, prefix):
    """enum 멤버에 prefix가 없으면 자동으로 붙입니다. 이미 있으면 그대로 반환합니다."""
    upper_name = member_name.upper()
    upper_prefix = prefix.upper()
    if upper_name.startswith(upper_prefix):
        return upper_name
    return upper_prefix + upper_name
