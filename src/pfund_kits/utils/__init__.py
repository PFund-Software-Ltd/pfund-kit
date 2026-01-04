from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from types import TracebackType
    from pfund_kits.enums.notebook_type import NotebookType
    LoggerName: TypeAlias = str

import os
import sys
import logging


_exception_loggers: set[LoggerName] = set()
def setup_exception_logging(logger_name: LoggerName):
    '''
    Catches all uncaught exceptions and logs them instead of just printing to console.
    
    Can be called multiple times with different logger names - the exception will
    be logged to all registered loggers.
    '''
    global _exception_loggers
    _exception_loggers.add(logger_name)

    def _custom_excepthook(exception_class: type[BaseException], exception: BaseException, traceback: TracebackType):
        for name in _exception_loggers:
            logging.getLogger(name).exception('Uncaught exception:', exc_info=(exception_class, exception, traceback))
    
    # Only set once to avoid multiple registrations (e.g. pfund and pfeed both call this)
    if not hasattr(sys, '_pfund_kits_excepthook_installed'):
        sys.excepthook = _custom_excepthook
        sys._pfund_kits_excepthook_installed = True


def get_notebook_type() -> NotebookType | None:
    import importlib.util
    
    marimo_spec = importlib.util.find_spec("marimo")
    if marimo_spec is not None:
        import marimo as mo
        if mo.running_in_notebook():
            return NotebookType.marimo
        
    if any(key.startswith(('JUPYTER_', 'JPY_')) for key in os.environ):
        return NotebookType.jupyter
    
    # if 'VSCODE_PID' in os.environ:
    #     return NotebookType.vscode
    
    # None means not in a notebook environment
    return None