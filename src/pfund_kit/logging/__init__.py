from __future__ import annotations
from typing import TYPE_CHECKING, Any, TypeAlias
if TYPE_CHECKING:
    from types import TracebackType
    from pfund_kit.config import Configuration
    LoggerName: TypeAlias = str

import sys
import logging


# Store registered logger names from packages using setup_exception_logging
_REGISTERED_EXCEPTHOOK_LOGGERS: set[str] = set()


def print_all_loggers(include_loggers_without_handlers: bool = False):
    for name in sorted(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        if logger.handlers:
            print(f"  {name}: {logger.handlers}")
        elif include_loggers_without_handlers:
            print(f"  {name}: no handlers")


def clear_logging_handlers(prefix: str = ''):
    '''Clears all handlers from all loggers.'''
    for logger_name in list(logging.Logger.manager.loggerDict):
        if prefix and not logger_name.startswith(prefix):
            continue
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:  # Copy list to avoid modification during iteration
            handler.close()
            logger.removeHandler(handler)


def setup_exception_logging(logger_name: str | None = None):
    '''
    Catches all uncaught exceptions and logs them to the appropriate package logger.

    Args:
        logger_name: The logger name to register (e.g., 'pfund', 'pfeed').
                    If provided, exceptions from this package will use this logger.
                    If None, falls back to root logger.

    Example:
        # In pfund/__init__.py
        setup_exception_logging('pfund')

        # In pfeed/__init__.py
        setup_exception_logging('pfeed')
    '''
    # Register the logger name if provided
    if logger_name:
        _REGISTERED_EXCEPTHOOK_LOGGERS.add(logger_name)

    def _get_logger_from_traceback(tb: TracebackType) -> logging.Logger:
        """Find the appropriate logger by scanning traceback for registered logger names."""
        # Walk through all frames in the traceback
        current_tb = tb
        while current_tb is not None:
            module_name = current_tb.tb_frame.f_globals.get('__name__', '')
            file_path = current_tb.tb_frame.f_code.co_filename

            for registered_logger in _REGISTERED_EXCEPTHOOK_LOGGERS:
                # Check module name (works when imported as module)
                if module_name.startswith(f'{registered_logger}.') or module_name == registered_logger:
                    return logging.getLogger(registered_logger)
                # Check file path (works when run as script with __main__)
                if f'/{registered_logger}/' in file_path:
                    return logging.getLogger(registered_logger)

            current_tb = current_tb.tb_next

        return logging.getLogger()  # fallback to root

    def _custom_excepthook(exception_class: type[BaseException], exception: BaseException, traceback: TracebackType):
        logger = _get_logger_from_traceback(traceback)
        logger.exception('Uncaught exception:', exc_info=(exception_class, exception, traceback))

    # Only set once to avoid multiple registrations
    if not hasattr(sys, '_pfund_kit_excepthook_installed'):
        sys.excepthook = _custom_excepthook
        sys._pfund_kit_excepthook_installed = True


def enable_debug_logging(logging_config: dict) -> dict:
    '''
    Enables debug logging by setting all loggers and handlers to DEBUG level.

    This function modifies the logging configuration to set:
    - All logger levels to DEBUG
    - All handler levels to DEBUG

    Args:
        logging_config: The logging config dict to modify.

    Returns:
        New logging config dict with DEBUG levels enabled everywhere.

    Example:
        >>> config = {'loggers': {'myapp': {'level': 'INFO'}}, 'handlers': {'console': {'level': 'INFO'}}}
        >>> debug_config = enable_debug_logging(config)
        >>> debug_config['loggers']['myapp']['level']
        'DEBUG'
    '''
    import copy
    result = copy.deepcopy(logging_config)

    # Set all logger levels to DEBUG
    if 'loggers' in result:
        for logger_config in result['loggers'].values():
            if isinstance(logger_config, dict):
                logger_config['level'] = 'DEBUG'

    # Set all handler levels to DEBUG
    if 'handlers' in result:
        for handler_config in result['handlers'].values():
            if isinstance(handler_config, dict):
                handler_config['level'] = 'DEBUG'

    # Set root logger level to DEBUG if it exists as a top-level key
    # (Note: root logger can also be specified inside 'loggers' with key '' or 'root',
    #  which would already be handled by the loop above)
    if 'root' in result and isinstance(result['root'], dict):
        result['root']['level'] = 'DEBUG'

    return result


def setup_logging(
    config: Configuration,
    env: str | None = None,
    reset: bool = False,
) -> None:
    '''Configure logging for a project.

    Args:
        config: The project's Configuration instance.
        env: Optional environment name used as a subdirectory of `config.log_path`.
        reset: If True, clear existing logging handlers before reconfiguring.
    '''
    from pfund_kit.logging.configurator import LoggingDictConfigurator

    if reset:
        clear_logging_handlers()

    log_path = config.log_path / env if env else config.log_path
    log_path.mkdir(parents=True, exist_ok=True)

    LoggingDictConfigurator.create(
        log_path=log_path,
        logging_config=get_logging_config(config),
        lazy=True,
        use_colored_logger=True,
    ).configure()

    setup_exception_logging(logger_name=config._paths.project_name)


def configure_logging(
    config: Configuration,
    overrides: dict[str, Any] | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    '''Load the project's logging.yml and merge it with optional overrides.

    Args:
        config: The project's Configuration instance.
        overrides: Dict merged on top of the loaded YAML.
        debug: If True, force all loggers/handlers to DEBUG level.

    Raises:
        FileNotFoundError: If the project's logging config YAML is missing.
    '''
    from pfund_kit.utils import deep_merge
    from pfund_kit.utils.yaml import load

    base = load(config.logging_config_file_path)
    if base is None:
        raise FileNotFoundError(
            f"Logging config file {config.logging_config_file_path} not found"
        )
    merged = deep_merge(base, overrides or {})
    logging_config = enable_debug_logging(merged) if debug else merged
    config._logging_config_cache = logging_config
    return logging_config


def get_logging_config(config: Configuration) -> dict[str, Any]:
    '''Return the merged logging config, caching it on the config instance.'''
    logging_config = getattr(config, '_logging_config_cache', None)
    if logging_config is None:
        logging_config = configure_logging(config)
    return logging_config


def add_logger_prefix(logging_config: dict, prefix: str) -> dict:
    '''
    Adds a prefix to all logger names in the logging config.

    Args:
        logging_config: The logging config dict.
        prefix: The prefix to add to logger names (e.g., 'pfeed', 'pfund').

    Returns:
        New logging config dict with prefixed logger names.

    Example:
        >>> config = {'loggers': {'root': {...}, 'myapp': {...}}}
        >>> add_logger_prefix(config, 'pfeed')
        {'loggers': {'pfeed': {...}, 'pfeed.myapp': {...}}}
    '''
    import copy
    result = copy.deepcopy(logging_config)

    if 'loggers' not in result:
        raise ValueError('logging_config must contain a "loggers" section')

    # Rename all loggers under 'loggers' section
    new_loggers = {}
    for logger_name, logger_config in result['loggers'].items():
        if logger_name in ['root', prefix]:
            new_logger_name = logger_name
        else:
            # Other loggers get prefixed (e.g., 'myapp' -> 'pfeed.myapp')
            new_logger_name = f'{prefix}.{logger_name}'
        new_loggers[new_logger_name] = logger_config

    result['loggers'] = new_loggers
    return result
