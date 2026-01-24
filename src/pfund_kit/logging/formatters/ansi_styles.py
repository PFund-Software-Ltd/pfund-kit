# VIBE-CODED
"""Convert Rich style strings to ANSI escape codes."""

from rich.style import Style


def style_to_ansi(style_str: str) -> str:
    """
    Convert Rich style string to ANSI escape codes using Rich's Style parser.

    This supports all Rich style attributes including:
    - Text styles: bold, dim, italic, underline, strike, etc.
    - Colors: All named colors from RichColor enum
    - Combined styles: "bold red", "italic bright_cyan", etc.

    Args:
        style_str: Rich style string like "bold red" or "italic cyan"

    Returns:
        ANSI escape code string

    Examples:
        >>> style_to_ansi("bold red")
        '\x1b[1;31m'
        >>> style_to_ansi("italic bright_green")
        '\x1b[3;92m'
        >>> style_to_ansi("bold underline cyan")
        '\x1b[1;4;36m'
    """
    if not style_str:
        return ''

    try:
        rich_style = Style.parse(style_str)
        # Use Rich's internal method to render ANSI codes
        # _make_ansi_codes returns (start_codes, end_codes) tuple
        from rich.console import Console

        # Create a console that forces terminal mode
        console = Console(force_terminal=True, legacy_windows=False)

        # Use render_str to get the ANSI codes
        with console.capture() as capture:
            console.print("X", style=rich_style, end="")

        output = capture.get()

        # Output is like: "\x1b[1;31mX\x1b[0m"
        # Extract just the opening codes (everything before 'X')
        if 'X' in output:
            return output.split('X')[0]

        return ''

    except Exception:
        return ''


# ANSI reset code
RESET = '\033[0m'


__all__ = ['style_to_ansi', 'RESET']
