from collections.abc import Callable

import click
from trogon import tui


def create_cli_group(
    name: str,
    with_tui: bool = True,
    init_context: Callable[[click.Context], None] | None = None,
    version: str | None = None,
    package_name: str | None = None,
):
    """
    Create a CLI group that can be extended by other packages.

    Args:
        name: Name of the CLI application
        with_tui: Whether to include the TUI interface
        init_context: Optional function that takes ctx and initializes ctx.obj
                           Example: lambda ctx: ctx.obj.update({'config': get_config()})
        version: Explicit version string for --version. If omitted, Click looks
                 up the installed metadata for `package_name`.
        package_name: Distribution name to read version from. Defaults to `name`
                      so e.g. create_cli_group('pfeed') reports pfeed's version
                      rather than pfund_kit's.

    Returns:
        Click Group that can be extended with commands
    """
    @click.group(
        name=name,
        context_settings={"help_option_names": ["-h", "--help"]}
    )
    @click.pass_context
    @click.version_option(version=version, package_name=package_name or name)
    def cli_group(ctx):
        ctx.ensure_object(dict)
        # Call custom context init function if provided
        if init_context:
            init_context(ctx)

    if with_tui:
        cli_group = tui(command='tui', help="Open terminal UI")(cli_group)

    return cli_group
