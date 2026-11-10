"""Utility functions for pfund_shell."""

import sys
from importlib.metadata import entry_points
from typing import Literal, cast

import click
from click import Command, Context, Group

# CLI-only commands, not offered or run inside pfund-shell: `tui` opens a
# full-screen app (trogon) that fights the shell's own prompt for the terminal
SHELL_DISABLED_COMMANDS = frozenset({"tui"})


def discover_command_groups() -> dict[str, click.Group]:
    """Discover command groups registered via entry points.

    Scans for entry points under 'pfund_shell.commands' namespace.
    Each entry point should provide a Click group object.

    Returns:
        Dict mapping command group names to Click Group objects.
    """
    command_groups = {}

    # Load entry points from 'pfund_shell.commands' namespace (Python 3.10+)
    shell_commands = entry_points().select(group="pfund_shell.commands")

    for ep in shell_commands:
        try:
            # Load the command group
            command_group = ep.load()
            command_groups[ep.name] = command_group
            print(f"✓ Loaded command group: {ep.name}")
        except Exception as e:
            import traceback

            print(f"✗ Failed to load {ep.name}: {e}", file=sys.stderr)
            traceback.print_exc()

    return command_groups


def is_group_command(
    command_group: click.Group, context_commands: list[str], command_name: str
) -> bool:
    """Check if a command is a group (has subcommands).

    Args:
        command_group: The Click group to check within
        context_commands: List of current context commands
        command_name: The command name to check

    Returns:
        True if the command is a group with subcommands
    """
    # Navigate through context to find the right group
    current_group = command_group
    for ctx_cmd in context_commands:
        cmd = current_group.commands.get(ctx_cmd)
        if isinstance(cmd, click.Group):
            current_group = cmd
        else:
            return False

    # Check if command_name is a group
    cmd = current_group.commands.get(command_name)
    return isinstance(cmd, click.Group)


def shell_commands(group: Group) -> list[tuple[str, Command]]:
    """(name, command) pairs to offer in the shell's completion and toolbar.

    Drops SHELL_DISABLED_COMMANDS, and when a command is registered under an
    alias too, keeps only the alias (`rm`, not `remove`; `compose`, not
    `docker-compose`) to keep the menu short. Every name still runs if typed.
    """
    aliased = {
        id(command) for name, command in group.commands.items() if name != command.name
    }
    return [
        (name, command)
        for name, command in group.commands.items()
        if name not in SHELL_DISABLED_COMMANDS
        and not (name == command.name and id(command) in aliased)
    ]


def _convert_click_command_to_dict(
    name: str, command: Command | Group, dict_value: Literal["help"] | None = None
) -> dict:
    """Converts a click command or group to {name: nested dict | help | None}.

    `name` is the name the command is registered under in its parent group, NOT
    `command.name`: an alias (e.g. `rm` for `remove`, `logs` for `log`) is the
    same Command object under a second key, so `command.name` would collapse it
    into the original and autocomplete would never offer it.

    A click group can have subcommands, which are also commands.
    This function will recursively convert all subcommands to dictionaries.

    Args:
        name: Name the command is registered under
        command: Click Command or Group to convert
        dict_value: if 'help', get the help text of the command, otherwise None

    Returns:
        Dictionary with command name as key and nested dict or None as value
    """
    commands_dict = {}
    if isinstance(command, Group):
        subcommands_dict: dict = {}
        for sub_name, sub_command in shell_commands(command):
            subcommands_dict.update(
                _convert_click_command_to_dict(sub_name, sub_command, dict_value)
            )
        commands_dict[name] = subcommands_dict
    elif isinstance(command, Command):
        ctx = Context(command)
        commands_dict[name] = command.get_help(ctx) if dict_value == "help" else None
    else:
        raise Exception(f"Unhandled click command type: {type(command)}")
    return commands_dict


def get_commands_dict(
    command_groups: dict[str, click.Group],
    pfund_shell_group: click.Group,
    base_command: str,
    context_commands: list[str] | None = None,
    dict_value: Literal["help"] | None = None,
) -> dict:
    """Build a nested dictionary of all available commands for autocompletion.

    Args:
        command_groups: Dict of registered command groups (pfeed, pfund, etc.)
        pfund_shell_group: The merged shell group with all commands
        base_command: Current context (e.g., 'pfund-shell', 'pfeed', 'pfund')
        context_commands: List of nested context commands (e.g., ['config'] for pfeed.config>)
        dict_value: if 'help', get the help text of the command, otherwise None

    Returns:
        Nested dictionary suitable for NestedCompleter
    """
    ctx = Context(pfund_shell_group)
    commands_dict = {}
    context_commands = context_commands or []
    is_base_command_pfund_shell = base_command == "pfund-shell"

    # If at root level (pfund-shell>), include all merged commands from shell_group
    if is_base_command_pfund_shell:
        for command in pfund_shell_group.list_commands(ctx):
            command_obj = pfund_shell_group.get_command(ctx, command)
            if command_obj:
                commands_dict.update(
                    _convert_click_command_to_dict(command, command_obj, dict_value)
                )

    # Add all command groups as top-level commands (but not if we're already in that context)
    for group_name, command_group in command_groups.items():
        # Skip adding the group if we're already inside it (e.g., don't show "pfeed" when in pfeed>)
        if base_command != group_name:
            commands_dict[group_name] = {}
            for name, command_obj in shell_commands(command_group):
                commands_dict[group_name].update(
                    _convert_click_command_to_dict(name, command_obj, dict_value)
                )

        # If we're in a specific group context, add its commands at root level
        if base_command == group_name:
            # Navigate through context commands to find the right group
            current_group = command_group
            for context_command in context_commands:
                # context commands are always groups (see is_group_command)
                current_group = cast(Group, current_group.commands[context_command])

            # Add commands from current context at root level for easier access
            for name, command_obj in shell_commands(current_group):
                commands_dict.update(
                    _convert_click_command_to_dict(name, command_obj, dict_value)
                )

    return commands_dict
