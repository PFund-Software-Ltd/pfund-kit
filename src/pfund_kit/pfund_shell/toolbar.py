"""Bottom toolbar for pfund_shell that displays available commands."""

import re
import textwrap

from prompt_toolkit.application import get_app

from pfund_kit.pfund_shell.utils import get_commands_dict

# Built-in commands that are always hidden from toolbar unless explicitly typed
HIDDEN_COMMANDS = ["help", "tutorial", "clear", "exit", "quit", "q"]


def format_commands_menu(commands, width=10, line_width=80):
    """Format the list into a nicely spaced menu that fits the terminal width."""
    rows = []
    current_row = []
    current_length = 0

    for command in commands:
        padded_command = command.ljust(width)
        if current_length + len(padded_command) > line_width:
            rows.append(" ".join(current_row))
            current_row = []
            current_length = 0

        current_row.append(padded_command)
        current_length += len(padded_command)

    if current_row:
        rows.append(" ".join(current_row))

    return "\n".join(rows)


def format_options_menu(
    help_text, alias_width=10, option_width=20, type_width=15, line_width=80
):
    """Format command options/help text into a nicely aligned menu."""
    # Remove the 'Usage' section and the 'Options' title
    help_text = re.sub(r"Usage:.*?Options:\n", "", help_text, flags=re.DOTALL)

    lines = help_text.strip().split("\n")
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        alias = ""
        option = ""
        variable_type = ""
        description = ""

        # Use regex to match the components
        match = re.match(
            r"(?P<alias>-\S+),?\s+(?P<option>--\S+)(?:\s+(?P<type>[A-Z]+))?\s+(?P<description>.+)",
            line,
        )
        if match:
            alias = match.group("alias").strip().rstrip(",")
            option = match.group("option").strip()
            variable_type = match.group("type") or ""
            description = match.group("description").strip()
        else:
            # Handle lines without an alias
            parts = line.split()
            i = 0

            if parts[i].startswith("-") and not parts[i].startswith("--"):
                alias = parts[i].rstrip(",")
                i += 1

            if i < len(parts) and parts[i].startswith("--"):
                option = parts[i]
                i += 1

            if i < len(parts) and parts[i].isupper():
                variable_type = parts[i]
                i += 1

            description = " ".join(parts[i:])

        # Calculate fixed fields length
        fixed_fields = f"{alias.ljust(alias_width)} {option.ljust(option_width)} {variable_type.ljust(type_width)}"
        fixed_length = len(fixed_fields)

        # Calculate available width for description
        available_width = line_width - fixed_length

        # Wrap the description
        wrapped_description = textwrap.wrap(description, width=available_width)
        if not wrapped_description:
            wrapped_description = [""]

        # Combine fixed fields with wrapped description
        formatted_line = f"{fixed_fields}{wrapped_description[0]}"
        formatted_lines.append(formatted_line)

        # Add any additional lines for the wrapped description
        for desc_line in wrapped_description[1:]:
            indent = " " * fixed_length
            formatted_lines.append(f"{indent}{desc_line}")

    return "\n".join(formatted_lines)


def bottom_toolbar(
    command_groups,
    pfund_shell_group,
    base_command: str,
    context_commands: list[str] | None = None,
):
    """Generate bottom toolbar showing available commands based on current input.

    Args:
        command_groups: Dict of registered command groups
        pfund_shell_group: The merged shell group
        base_command: Current context (e.g., 'pfund-shell', 'pfeed')
        context_commands: List of nested context commands

    Returns:
        Formatted string to display in the bottom toolbar
    """
    commands_dict = get_commands_dict(
        command_groups,
        pfund_shell_group,
        base_command,
        context_commands=context_commands,
        dict_value="help",
    )

    # Get the terminal width
    app = get_app()
    line_width = app.output.get_size().columns

    # Get current text in the prompt
    current_text = app.current_buffer.text
    command_splits = current_text.split()

    # Hide built-in commands unless they are the first command
    if not command_splits or command_splits[0] not in HIDDEN_COMMANDS:
        for command in HIDDEN_COMMANDS:
            commands_dict.pop(command, None)

    # Navigate through the command hierarchy based on current input
    if command_splits:
        for command in command_splits:
            if command not in commands_dict:
                break
            commands_dict = commands_dict[command]
            # If we've reached help text, format it as options menu
            if isinstance(commands_dict, str):
                menu = format_options_menu(
                    commands_dict, option_width=20, line_width=line_width
                )
                return menu

    # Format remaining commands as a menu
    menu = format_commands_menu(commands_dict, width=12, line_width=line_width)
    return menu
