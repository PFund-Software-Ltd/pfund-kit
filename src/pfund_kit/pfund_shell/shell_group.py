"""Command collection for pfund_shell.

Creates a unified command namespace by merging all registered command groups,
allowing users to call commands directly without prefixing the project name.
"""

import click

# Import shared commands from pfund-kit
from pfund_kit.cli.commands import config, docker_compose, remove, doc

# Shared commands that will be added to shell_group and excluded from project groups
SHARED_COMMANDS = [config, docker_compose, remove, doc]


class ShellCommandCollection(click.CommandCollection):
    """Command collection that merges all registered command groups.

    This allows users to type commands directly at the pfund-shell> prompt
    without needing to specify the project name, as long as there's no ambiguity.

    Shared commands from pfund-kit (config, docker-compose, remove, doc) are
    excluded from individual projects to avoid conflicts, since they're available
    as shell built-ins.
    """

    # Command names (and their aliases) to exclude from project groups (derived from SHARED_COMMANDS)
    SHARED_COMMAND_NAMES = {cmd.name for cmd in SHARED_COMMANDS} | {'tui', 'compose', 'rm'}

    def get_command(self, ctx, name):
        """Get a command by name, searching through all source groups."""
        # Skip shared commands - they're handled separately
        if name in self.SHARED_COMMAND_NAMES:
            return None

        # Search through all registered command groups
        for source in self.sources:
            command = source.get_command(ctx, name)
            if command:
                return command
        return None

    def list_commands(self, ctx):
        """List all available commands from all source groups."""
        commands = []
        for source in self.sources:
            source_commands = source.list_commands(ctx)
            for name in source_commands:
                # Skip shared commands
                if name in self.SHARED_COMMAND_NAMES:
                    continue
                commands.append(name)

        # Remove duplicates and sort
        return sorted(set(commands))


def create_pfund_shell_group(command_groups: dict):
    """Create the shell group after command_groups is populated."""
    @click.group(cls=ShellCommandCollection, sources=list(command_groups.values()))
    def pfund_shell_group():
        pass

    return pfund_shell_group
