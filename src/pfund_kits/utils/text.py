import re


def to_camel_case(snake_case_str: str) -> str:
    return ''.join(word.capitalize() for word in snake_case_str.lower().split('_'))


def to_snake_case(s: str) -> str:
    """
    Convert a CamelCase or PascalCase string to snake_case.
    Example:
        >>> to_snake_case("YahooFinance")
        'yahoo_finance'
    """
    # Insert underscore before each uppercase letter (that’s not at the start),
    # then lowercase the whole thing.
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
    return snake


def to_uppercase(*args: str) -> tuple[str, ...]:
    return tuple(arg.upper() for arg in args)


def to_lowercase(*args: str) -> tuple[str, ...]:
    return tuple(arg.lower() for arg in args)
