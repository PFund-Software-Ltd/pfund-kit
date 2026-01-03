from rich import print as rprint
from rich.pretty import pprint as rpprint
from rich.console import Console

from pfund_kits.utils.rich_style import RichColor, RichTextStyle, RichStyle


console = Console()
cprint = console.print


__all__ = (
    'rprint', 
    'rpprint', 
    'cprint',
    'console',
    'RichColor', 
    'RichTextStyle', 
    'RichStyle',
)