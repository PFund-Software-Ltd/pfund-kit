from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund_kits.enums.notebook_type import NotebookType

import os


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