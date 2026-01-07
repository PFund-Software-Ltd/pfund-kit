import os
import shutil
from pathlib import Path

import click


@click.group()
def clear():
    """Clear caches, data and logs."""
    pass


def _clear_path(base_path: Path, target: str | None, path_name: str, ctx):
    """Shared logic for clearing cache/data/log paths.

    Args:
        base_path: The base directory path (e.g., config.cache_path)
        target: Optional target file/folder within base_path
        path_name: Display name for messages (e.g., "Cache", "Data", "Log")
        ctx: Click context for exiting
    """
    # If no target specified, clear entire directory
    if not target:
        target_path = base_path
        clear_all = True
    else:
        target_path = base_path / target
        clear_all = False

        # If exact match doesn't exist, try case-insensitive match
        if not target_path.exists() and base_path.exists():
            # Look for case-insensitive match in the directory
            for item in base_path.iterdir():
                if item.name.lower() == target.lower():
                    target_path = item
                    click.echo(f"Found '{item.name}' (case-insensitive match for '{target}')")
                    break

    # Check if target exists
    if not target_path.exists():
        if clear_all:
            click.echo(f"{path_name} directory not found at {base_path}")
            ctx.exit(1)
        else:
            click.echo(f"Error: '{target}' not found in {base_path}", err=True)
            ctx.exit(1)

    try:
        # Clear the target
        if target_path.is_file():
            click.echo(f"Removing file: {target_path}")
            target_path.unlink()
            click.echo(f"{path_name} file cleared successfully!")
        elif target_path.is_dir():
            if clear_all:
                click.echo(f"Clearing entire {path_name.lower()} directory: {base_path}")
                shutil.rmtree(base_path)
                os.makedirs(base_path, exist_ok=True)
                click.echo(f"{path_name} directory cleared successfully!")
            else:
                click.echo(f"Removing folder: {target_path}")
                shutil.rmtree(target_path)
                click.echo(f"{path_name} folder cleared successfully!")
    except Exception as e:
        click.echo(f"Error clearing {path_name.lower()}: {str(e)}", err=True)
        ctx.exit(1)


@clear.command()
@click.pass_context
@click.argument('target', type=str, required=False)
def cache(ctx, target):
    """Clear cache directory or specific cache files/folders.

    Examples:
        pfeed clear cache              # Clear entire cache directory
        pfeed clear cache api          # Clear cache/api folder
        pfeed clear cache models.pkl   # Clear cache/models.pkl file
    """
    config = ctx.obj['config']
    _clear_path(config.cache_path, target, "Cache", ctx)


@clear.command()
@click.pass_context
@click.argument('target', type=str, required=False)
def data(ctx, target):
    """Clear data directory or specific data files/folders.

    Examples:
        pfeed clear data               # Clear entire data directory
        pfeed clear data minio         # Clear data/minio folder
        pfeed clear data backup.db     # Clear data/backup.db file
    """
    config = ctx.obj['config']
    _clear_path(config.data_path, target, "Data", ctx)


@clear.command()
@click.pass_context
@click.argument('target', type=str, required=False)
def log(ctx, target):
    """Clear log directory or specific log files/folders.

    Examples:
        pfeed clear log                # Clear entire log directory
        pfeed clear log app            # Clear log/app folder
        pfeed clear log error.log      # Clear log/error.log file
    """
    config = ctx.obj['config']
    _clear_path(config.log_path, target, "Log", ctx)
