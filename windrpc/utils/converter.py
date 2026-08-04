import re


def to_pascal_case(snake_str):
    """Converts a snake_case or camelCase string to PascalCase."""
    if not snake_str or not isinstance(snake_str, str):
        return ""
    if '_' in snake_str:
        return "".join(word.capitalize() for word in snake_str.split('_'))
    return snake_str[0].upper() + snake_str[1:]


def to_upper_snake_case(name):
    """Converts a PascalCase or camelCase string to UPPER_SNAKE_CASE.
    Example: 'PowerMode' -> 'POWER_MODE', 'StatusCode' -> 'STATUS_CODE'
    """
    if not name or not isinstance(name, str):
        return ""
    # Handle consecutive uppercase letters (acronyms): 'HTTPStatus' -> 'HTTP_Status'
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    # Insert underscore between lowercase and uppercase boundaries
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.upper()


def enum_value_prefix(enum_name, explicit_prefix=None):
    """Returns the enum value prefix according to Protobuf style guidelines.

    If explicit_prefix is specified, use it; otherwise automatically derive from enum type name.
    Example: enum_name='PowerMode' -> 'POWER_MODE_'
             enum_name='StatusCode', explicit_prefix='SC' -> 'SC_'
    """
    if explicit_prefix:
        prefix = explicit_prefix.rstrip('_').upper()
    else:
        prefix = to_upper_snake_case(enum_name)
    return prefix + '_'


def apply_enum_prefix(member_name, prefix):
    """Applies prefix to enum member if missing; returns as-is if already present."""
    upper_name = member_name.upper()
    upper_prefix = prefix.upper()
    if upper_name.startswith(upper_prefix):
        return upper_name
    return upper_prefix + upper_name
