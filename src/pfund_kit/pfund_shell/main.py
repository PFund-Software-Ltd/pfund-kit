"""pfund_shell: Interactive shell for pfund ecosystem commands.

This module provides an interactive shell that dynamically discovers
and loads command groups from installed packages via entry points.
"""

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from pfund_kit.pfund_shell.help import display_help
from pfund_kit.pfund_shell.toolbar import bottom_toolbar
from pfund_kit.pfund_shell.tutorial import display_tutorial
from pfund_kit.pfund_shell.utils import (
    SHELL_DISABLED_COMMANDS,
    discover_command_groups,
    get_commands_dict,
    is_group_command,
)

COMMANDS = ["help", "tutorial", "clear", "exit"]
EXIT_COMMANDS = ["exit", "quit", "q"]
TEXT_COLOR = "#f49f31"  # or #fb8b1e
STYLE = Style.from_dict(
    {
        "": f"fg:{TEXT_COLOR}",  # Input text color
        "completion-menu": f"bg:{TEXT_COLOR}",
        "bottom-toolbar": "bold",
    }
)


def get_completer(
    command_groups,
    pfund_shell_group,
    base_command,
    context_commands: list[str] | None = None,
):
    from prompt_toolkit.completion import NestedCompleter

    commands_dict = get_commands_dict(
        command_groups,
        pfund_shell_group,
        base_command,
        context_commands=context_commands,
    )
    # Only add built-in commands at root level (pfund-shell>)
    if base_command == "pfund-shell":
        for command in COMMANDS:
            commands_dict[command] = None
    completer = NestedCompleter.from_nested_dict(commands_dict)
    return completer


def start_shell():
    """Start the interactive pfund shell.

    Features:
    1. Discover command groups via entry points
    2. Context switching (e.g., pfeed>)
    3. Nested contexts (e.g., pfeed.config>)
    4. Execute commands using Click
    """
    from pfund_kit.pfund_shell.shell_group import (
        ShellCommandCollection,
        create_pfund_shell_group,
    )

    # Discover all registered command groups
    command_groups = discover_command_groups()

    if not command_groups:
        print(
            "No command groups found. Please install packages with pfund_shell.commands entry points."
        )
        print("\nExample pyproject.toml configuration:")
        print('[project.entry-points."pfund_shell.commands"]')
        print('pfeed = "pfeed.cli:pfeed_group"')
        return

    # Create the unified command collection for root-level commands
    # This merges all commands from all registered projects (pfeed, pfund, etc.)
    # into a single namespace, allowing users to type commands directly without
    # prefixing the project name (e.g., "download" instead of "pfeed download").
    # Shared commands from pfund-kit (config, remove, etc.) are also added
    # and excluded from individual projects to avoid conflicts.
    pfund_shell_group = create_pfund_shell_group(command_groups)

    print(f"\nWelcome to PFund Shell! Loaded {len(command_groups)} command group(s).")
    print("Available commands:", ", ".join(command_groups.keys()))
    print(
        'Type "tutorial" to learn how to use the shell, or "help" to see all commands.'
    )
    print('Type "exit" or "quit" to exit.\n')

    # Shell state
    base_command = "pfund-shell"  # Current project context (pfeed, pfund, etc.)
    context_commands: list[
        str
    ] = []  # Nested context (e.g., ['config'] for pfeed.config>)
    prompt_label = f"{base_command}> "

    # Create PromptSession for better input handling
    session = PromptSession(style=STYLE, key_bindings=KeyBindings())

    # Main shell loop
    while True:
        try:
            # Get user input with dynamic completer and bottom toolbar
            command = session.prompt(
                prompt_label,
                completer=get_completer(
                    command_groups, pfund_shell_group, base_command, context_commands
                ),
                bottom_toolbar=lambda base_command=base_command, context_commands=context_commands: (
                    bottom_toolbar(
                        command_groups,
                        pfund_shell_group,
                        base_command,
                        context_commands,
                    )
                ),
            )
            command_splits = command.split()

            if not command_splits:
                continue

            first_command = command_splits[0]

            # Handle clear command
            if first_command == "clear":
                # Clear the terminal screen
                print("\033[2J\033[H", end="")
                continue

            # Handle tutorial command
            if first_command == "tutorial":
                display_tutorial()
                continue

            # Handle help command
            if first_command == "help":
                display_help(command_groups)
                continue

            # Handle exit commands
            if first_command in EXIT_COMMANDS:
                if base_command != "pfund-shell":
                    # Exit from project context back to root
                    base_command = "pfund-shell"
                    prompt_label = "pfund-shell> "
                    context_commands = []
                    continue
                else:
                    # Exit shell entirely
                    break

            # e.g. "tui" (root or pfeed>) or "pfeed tui"
            if first_command in command_groups and len(command_splits) > 1:
                command_name, project = command_splits[1], first_command
            else:
                command_name = first_command
                project = (
                    base_command
                    if base_command != "pfund-shell"
                    else next(iter(command_groups))
                )
            if not context_commands and command_name in SHELL_DISABLED_COMMANDS:
                click.echo(
                    f"'{command_name}' is not available in pfund-shell, "
                    f"run '{project} {command_name}' in your terminal instead."
                )
                continue

            # Route the command
            # Check if user is switching to a registered command group
            is_switching_context = first_command in command_groups

            if base_command != "pfund-shell" or is_switching_context:
                # We're inside a project context OR user is switching to one

                if is_switching_context:
                    # User explicitly typed a project name (e.g., "pfeed")
                    target_command_group = first_command
                else:
                    # Use current base_command
                    target_command_group = base_command

                command_group = command_groups[target_command_group]

                # Single word command - might be context switch
                if len(command_splits) == 1:
                    if is_switching_context:
                        # Switch base command: pfund-shell> -> pfeed>
                        context_commands = []
                        base_command = target_command_group
                        prompt_label = f"{base_command}> "
                        print(
                            f"Switched to {base_command} (type '{'/'.join(EXIT_COMMANDS)}' to go back)"
                        )
                        continue
                    else:
                        # Check if it's a nested group: pfeed> config -> pfeed.config>
                        if is_group_command(
                            command_group, context_commands, first_command
                        ):
                            # Show help for the group
                            # temp_args = []
                            # for cmd in context_commands[::-1]:
                            #     temp_args.insert(0, cmd)
                            # temp_args.append(first_command)
                            # try:
                            #     command_group.main(args=temp_args, standalone_mode=False)
                            # except click.exceptions.ClickException as e:
                            #     e.show()
                            # Then switch context
                            prompt_label = f"{prompt_label[:-2]}.{first_command}> "
                            context_commands.append(first_command)
                            continue

                # Prepare arguments for Click
                if is_switching_context:
                    # Remove project name from args: ["pfeed", "config", "list"] -> ["config", "list"]
                    command_splits.remove(first_command)
                else:
                    # Prepend context commands: user typed "list" in pfeed.config>
                    # Add context in reverse: ["list"] -> ["config", "list"]
                    for cmd in context_commands[::-1]:
                        command_splits.insert(0, cmd)

                # Execute via the specific command group
                try:
                    command_group.main(
                        args=command_splits,
                        standalone_mode=False,
                        prog_name=target_command_group,
                    )
                except click.exceptions.ClickException as e:
                    e.show()
            elif first_command in ShellCommandCollection.SHARED_COMMAND_NAMES:
                # Shared commands (remove, config, ...) act on ONE project's paths,
                # so at root it's ambiguous which project is meant. Never guess:
                # picking the first group would e.g. delete the wrong project's data.
                typed = " ".join(command_splits)
                examples = " / ".join(f"'{name} {typed}'" for name in command_groups)
                click.echo(
                    f"'{first_command}' is per-project, which one? "
                    f"Type {examples}, or switch first (e.g. "
                    f"'{next(iter(command_groups))}')."
                )
            else:
                # We're at root level - find which command group owns this command
                # and invoke through that group to ensure proper context setup (ctx.obj)
                owner_group = None
                owner_name = None
                for group_name, group in command_groups.items():
                    if group.get_command(click.Context(group), first_command):
                        owner_group = group
                        owner_name = group_name
                        break

                if owner_group:
                    # Invoke through the owning group so its callback sets up ctx.obj
                    try:
                        owner_group.main(
                            args=command_splits,
                            standalone_mode=False,
                            prog_name=owner_name,
                        )
                    except click.exceptions.ClickException as e:
                        e.show()
                else:
                    # Command not found in any group
                    click.echo(f"Unknown command: {first_command}")

        except KeyboardInterrupt:  # Handle Ctrl+C
            print()  # New line
            continue
        except EOFError:  # Handle Ctrl+D
            print()  # New line
            break

    print("\nGoodbye! Thanks for using PFund Shell.")
    print(
        "⭐ Enjoying it? Star us on GitHub: https://github.com/PFund-Software-Ltd/pfund"
    )
    print(
        "💬 Feedback & suggestions: https://github.com/PFund-Software-Ltd/pfund-kit/issues"
    )


if __name__ == "__main__":
    start_shell()
