import subprocess

import click


def handle_passthrough_help(
    ctx: click.Context,
    underlying_command: list[str],
    show_underlying: bool = True,
    help_flags: tuple[str, ...] = ("--help", "-h"),
) -> None:
    """Handle --help for commands that pass through to underlying tools.

    Shows both Click's help (custom options) and the underlying tool's help.

    Args:
        ctx: Click context
        underlying_command: Command to show help for
        show_underlying: Whether to show underlying tool's help (default: True)
        help_flags: Flags that trigger help display (default: ("--help", "-h"))
                   Use ("--help",) if -h is reserved by the underlying tool
    """
    import click
    # Check if any help flag is present
    if any(flag in ctx.args for flag in help_flags):
        # Show Click's help first (our custom options)
        click.echo(ctx.get_help())

        # Then show underlying tool's help if requested
        if show_underlying:
            click.echo("\n" + "=" * 60)
            click.echo(f"Additional options from '{' '.join(underlying_command)}':")
            click.echo("=" * 60 + "\n")
            subprocess.run([*underlying_command, "--help"])

        ctx.exit(0)


def cli_args_to_kwargs(args):
    """
    Convert Click's extra CLI arguments into a kwargs dictionary.
    
    Transforms a list of command-line arguments (from Click's ctx.args) into
    a dictionary suitable for **kwargs unpacking. This enables CLI commands
    to accept dynamic, data-source-specific parameters without predefining them.
    
    Args:
        args (list): Raw argument list from Click context (ctx.args)
    
    Returns:
        dict: Dictionary ready for **kwargs unpacking, where:
            - Keys have dashes converted to underscores
            - Flags without values are set to True
            - Non-option arguments are ignored
    
    Examples:
        >>> cli_args_to_kwargs(['--exchange', 'BYBIT', '--symbol', 'BTC'])
        {'exchange': 'BYBIT', 'symbol': 'BTC'}
        
        >>> cli_args_to_kwargs(['--verbose', '--timeout', '30'])
        {'verbose': True, 'timeout': '30'}
        
        >>> cli_args_to_kwargs(['--some-key', 'value'])
        {'some_key': 'value'}
    """
    kwargs = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            # Replace dashes with underscores for Python-friendly kwarg keys
            key = arg[2:].replace("-", "_")
            # Check if there's a following value that isn't another option
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                # Flag without value becomes True
                kwargs[key] = True
                i += 1
        else:
            # Skip non-option arguments
            i += 1
    return kwargs