import re


def to_camel_case(snake_case_str: str) -> str:
    pascal_case_str = to_pascal_case(snake_case_str)
    return pascal_case_str[:1].lower() + pascal_case_str[1:]


def to_pascal_case(s: str) -> str:
    return ''.join(word.capitalize() for word in to_snake_case(s).split('_'))


def to_snake_case(s: str) -> str:
    """Convert a string from common naming conventions to snake_case."""
    s = re.sub(r'[\s-]+', '_', s.strip())
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return re.sub(r'_+', '_', s).strip('_').lower()


def to_uppercase(*args: str) -> tuple[str, ...]:
    return tuple(arg.upper() for arg in args)


def to_lowercase(*args: str) -> tuple[str, ...]:
    return tuple(arg.lower() for arg in args)
