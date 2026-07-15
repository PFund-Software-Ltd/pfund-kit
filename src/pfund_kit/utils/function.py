import inspect
from typing import Callable, Any


def get_function_signature(function: object, skip_self_and_cls: bool=True) -> inspect.Signature:
    """
    Returns the function signature.

    If skip_self_and_cls is True, removes 'self' and 'cls' from the parameters.
    """
    signature = inspect.signature(function)
    if skip_self_and_cls and signature.parameters:
        # Get first parameter name
        first_param_name = next(iter(signature.parameters))
        if first_param_name in ('self', 'cls'):
            # Remove only the first parameter
            params = list(signature.parameters.values())[1:]
            signature = signature.replace(parameters=params)
    return signature


def get_function_args_and_kwargs(
    function: Callable[..., Any],
    skip_self_and_cls: bool=True,
) -> tuple[list[str], dict[str, Any], str | None, str | None]:
    """
    Parses the function's signature into:
    - a list of required positional/keyword arguments (without defaults),
    - a dict of keyword arguments with default values,
    - the name of *args if present,
    - the name of **kwargs if present.
    """
    signature = get_function_signature(function, skip_self_and_cls=skip_self_and_cls)
    args: list[str] = []
    kwargs: dict[str, Any] = {}
    var_args = var_kwargs = None
    # Iterate over the parameters of the signature
    for name, param in signature.parameters.items():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            # This is *args
            var_args = name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            # This is **kwargs
            var_kwargs = name
        elif param.default is inspect.Parameter.empty:
            # Regular positional argument
            args.append(name)
        else:
            # Keyword argument with a default value
            kwargs[name] = param.default
    return args, kwargs, var_args, var_kwargs
