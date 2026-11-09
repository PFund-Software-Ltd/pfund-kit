from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def display_tutorial():
    """Display tutorial explaining how to use the pfund shell."""
    console = Console()

    # Three ways to run commands
    tutorial_text = Text()
    tutorial_text.append("There are ", style="white")
    tutorial_text.append("three ways", style="bold yellow")
    tutorial_text.append(" to run commands:\n\n", style="white")

    tutorial_text.append("1. Direct command (recommended):\n", style="bold cyan")
    tutorial_text.append("   pfund-shell> backtest\n", style="dim")
    tutorial_text.append(
        "   Type commands directly without prefix if there's no ambiguity\n\n",
        style="white",
    )

    tutorial_text.append("2. Full command syntax:\n", style="bold cyan")
    tutorial_text.append("   pfund-shell> pfund backtest\n", style="dim")
    tutorial_text.append(
        "   Use full syntax when commands overlap between projects\n\n", style="white"
    )

    tutorial_text.append("3. Context switching:\n", style="bold cyan")
    tutorial_text.append("   pfund-shell> pfund\n", style="dim")
    tutorial_text.append("   Switched to pfund\n", style="dim green")
    tutorial_text.append("   pfund> backtest\n", style="dim")
    tutorial_text.append(
        "   Switch to a command group first, then run commands within that context\n\n",
        style="white",
    )

    tutorial_text.append("Built-in commands:\n", style="bold cyan")
    tutorial_text.append("  • help     - Show all available commands\n", style="white")
    tutorial_text.append("  • tutorial - Show this tutorial\n", style="white")
    tutorial_text.append("  • clear    - Clear the terminal screen\n", style="white")
    tutorial_text.append(
        "  • exit/quit/q - Exit the shell (or go back to root context)\n", style="white"
    )

    panel = Panel(
        tutorial_text,
        title="[bold]How to Use PFund Shell[/bold]",
        border_style="blue",
        padding=(1, 2),
    )

    console.print(panel)
    console.print()
