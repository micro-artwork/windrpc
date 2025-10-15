def to_pascal_case(snake_str):
    """snake_case 또는 camelCase 문자열을 PascalCase로 변환합니다."""
    if not snake_str or not isinstance(snake_str, str):
        return ""
    if '_' in snake_str:
        return "".join(word.capitalize() for word in snake_str.split('_'))
    return snake_str[0].upper() + snake_str[1:]
