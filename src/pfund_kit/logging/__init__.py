from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from types import TracebackType
    LoggerName: TypeAlias = str
    
import sys
import logging


# Store registered logger names from packages using setup_exception_logging
_REGISTERED_EXCEPTHOOK_LOGGERS: set[str] = set()


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
