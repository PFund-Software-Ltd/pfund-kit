import shutil
from pathlib import Path

import click


def auto_detect_editor():
    """Auto-detect an available code editor from popular choices."""
    import shutil

    # List of popular editors in order of preference
    editors = ['cursor', 'code', 'zed', 'charm', 'nvim']

    for cmd in editors:
        if shutil.which(cmd):
            return cmd
    return None


def open_file_with_editor(file_path: Path, editor_cmd: str):
    """Open file with the specified editor, handling edge cases like Cursor's space bug."""
    import subprocess
    import platform

    file_path_str = str(file_path)

    try:
        # Cursor CLI has a bug with spaces in paths, use shell mode with quotes
        if editor_cmd == 'cursor':
            if platform.system() != 'Windows':
                # On macOS/Linux: escape spaces with backslashes AND wrap in quotes
                escaped_path = file_path_str.replace(' ', r'\ ')
                subprocess.run(f'{editor_cmd} "{escaped_path}"', shell=True, check=True)
            else:
                # On Windows: use quotes (standard Windows shell escaping)
                # Note: If this doesn't work, Windows may have the same bug
                subprocess.run(f'{editor_cmd} "{file_path_str}"', shell=True, check=True)
        else:
            # All other editors: use standard subprocess list approach (safest)
            subprocess.run([editor_cmd, file_path_str], check=True)
    except FileNotFoundError:
        click.echo(f"Error: Editor '{editor_cmd}' not found. Please check if it's installed and in your PATH.", err=True)
        raise
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to open file with '{editor_cmd}': {e}", err=True)
        raise


@click.group()
def config():
    """Manage configuration settings."""
    pass


@config.command()
@click.pass_context
def where(ctx):
    """Print the config path."""
    config = ctx.obj['config']
    click.echo(config.path)

    
    
@config.command('list')
@click.pass_context
def list_config(ctx):
    """Print the config file."""
    from pprint import pformat
    config = ctx.obj['config']
    config_dict = config.to_dict()
    content = click.style(pformat(config_dict), fg='green')
    click.echo(f"File: {config.file_path}\n{content}")


@config.command('open')
@click.pass_context
@click.option('--config-file', '--config', '-c', is_flag=True, help='Open the config file')
@click.option('--docker-file', '--docker', '-d', is_flag=True, help='Open the compose.yml file')
@click.option('--logging-file', '--logging', '-l', is_flag=True, help='Open the logging.yml file')
@click.option('--default-editor', '-e', is_flag=True, help='Use system default editor ($VISUAL or $EDITOR)')
@click.argument('editor', required=False)
def open_config(ctx, config_file, logging_file, docker_file, default_editor, editor):
    """Opens the config files, e.g. logging.yml, docker-compose.yml.

    EDITOR is the optional editor command to use (e.g., "code", "vim", "subl").
    If not specified, prints the file path.

    Examples:
        pfeed config open -l code         # Open logging file in VS Code
        pfeed config open -c vim          # Open config file in vim
        pfeed config open -d -E           # Open docker file in default editor
        pfeed config open -l              # Just print the logging file path
    """
    import subprocess

    config = ctx.obj['config']
    paths = config._paths
    project_name = paths.project_name

    if sum([config_file, logging_file, docker_file]) > 1:
        click.echo('Please specify only one file to open')
        return

    # Determine which file to open
    if config_file:
        file_path = config.file_path
    elif logging_file:
        file_path = config.logging_config_file_path
    elif docker_file:
        file_path = config.docker_compose_file_path
    else:
        click.echo(f'Please specify a file to open, run "{project_name} config open --help" for more info')
        return
    
    # Handle opening the file
    if default_editor:
        # Use Click's built-in editor (respects $VISUAL/$EDITOR)
        click.edit(filename=str(file_path))
    else:
        # Auto-detect editor if not specified
        editor = editor or auto_detect_editor()

        if editor:
            try:
                open_file_with_editor(file_path, editor)
                # Get display name for the editor
                editor_names = {
                    'cursor': 'Cursor',
                    'code': 'VS Code',
                    'zed': 'Zed',
                    'charm': 'PyCharm',
                    'nvim': 'Neovim',
                }
                display_name = editor_names.get(editor, editor)
                click.echo(f"Opened {project_name}'s {file_path.name} with {display_name}")
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass  # Error already printed by open_file_with_editor
        else:
            # No editor found, print helpful message
            click.echo("No code editor detected.", err=True)
            click.echo(f"Tip: Specify an editor (e.g., '{project_name} config open -l code' to use VS Code) or use -E for system default editor", err=True)
            click.echo(f"\nFile location: {file_path}")


@config.command('set')
@click.pass_context
@click.option('--data-path', '--data', type=click.Path(resolve_path=True), help='Set the data path')
@click.option('--log-path', '--log', type=click.Path(resolve_path=True), help='Set the log path')
@click.option('--cache-path', '--cache', type=click.Path(resolve_path=True), help='Set the cache path')
def set_config(ctx, data_path, log_path, cache_path):
    """Update configuration paths.

    Examples:
        pfeed config set --data /path/to/data
        pfeed config set --log /var/log/pfeed --cache /tmp/cache
    """
    config = ctx.obj['config']

    # Check if at least one option is provided
    if not any([data_path, log_path, cache_path]):
        click.echo("Error: Please specify at least one path to update.", err=True)
        click.echo("Run 'config set --help' for usage information.")
        return

    # Update configuration and track changes
    updated = []
    if data_path:
        config.data_path = Path(data_path)
        updated.append(f"data_path -> {data_path}")
    if log_path:
        config.log_path = Path(log_path)
        updated.append(f"log_path -> {log_path}")
    if cache_path:
        config.cache_path = Path(cache_path)
        updated.append(f"cache_path -> {cache_path}")

    config.save()
    click.echo(f"Updated {config.filename}:")
    for change in updated:
        click.echo(f"  {change}")


@config.command()
@click.pass_context
@click.option('--config-file', '--config', '-c', is_flag=True, help='Reset the config file')
@click.option('--logging-file', '--logging', '-l', is_flag=True, help='Reset the logging.yaml file')
@click.option('--docker-file', '--docker', '-d', is_flag=True, help='Reset the compose.yml file')
def reset(ctx, config_file, logging_file, docker_file):
    """Reset the configuration to defaults.
    If no flags were set, all files will be reset.
    Args:
        config_file: Reset the config file
        docker_file: Reset the compose.yml file
        logging_file: Reset the logging.yaml file for logging config
    """
    config = ctx.obj['config']
    
    # If no flags were set, set all to True
    if not any([config_file, logging_file, docker_file]):
        config_file = logging_file = docker_file = True
    
    paths = config._paths
    project_name = paths.project_name
    
    def _reset_file(filename, has_default_file=True):
        user_file = config.path / filename
        backup_file = config.path / f'{filename}.bak'

        # Backup existing user file if it exists
        if user_file.exists():
            shutil.copy(user_file, backup_file)
            click.echo(f"  Backed up the existing file {user_file.name} to {backup_file.name}")

        if has_default_file:
            default_file = paths.package_path / filename
            if not default_file.exists() and paths.project_root:
                default_file = paths.project_root / filename
                
            # Copy default file to user location
            if default_file.exists():
                shutil.copy(default_file, user_file)
                click.echo(f"  Restored from default file {default_file.name}")
            else:
                click.echo(f"  Warning: Default file {default_file.name} not found, skipping", err=True)

    if config_file:
        filename = config.filename
        click.echo(f"Resetting {project_name}'s {filename}...")
        _reset_file(filename, has_default_file=False)
        config.save()

    if logging_file:
        filename = config.LOGGING_CONFIG_FILENAME
        click.echo(f"Resetting {project_name}'s {filename}...")
        _reset_file(filename)

    if docker_file:
        filename = config.DOCKER_COMPOSE_FILENAME
        click.echo(f"Resetting {project_name}'s {filename}...")
        _reset_file(filename)

