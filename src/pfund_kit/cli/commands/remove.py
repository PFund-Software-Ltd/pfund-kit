from __future__ import annotations

import os
import shutil
from pathlib import Path

import click


@click.group()
def remove() -> None:
    """Remove caches, data and logs."""


def _is_inside(base_path: Path, target_path: Path) -> bool:
    """True if target_path is strictly inside base_path (not base_path itself).

    The parent is resolved (following symlinks) but the last component is not,
    so a symlink inside base_path counts as inside even if it points elsewhere.
    """
    if target_path.name in ("", ".", ".."):
        return False
    resolved_base = base_path.resolve()
    candidate = target_path.parent.resolve() / target_path.name
    return candidate != resolved_base and candidate.is_relative_to(resolved_base)


def _confirm(question: str) -> bool:
    """Ask y/N (default No). Ctrl+C / Ctrl+D / no stdin count as No.

    click.confirm raises click.Abort on those, which pfund-shell doesn't catch
    (it only catches ClickException), so swallow it here.
    """
    try:
        return click.confirm(question, default=False)
    except click.Abort:
        click.echo()
        return False


def _is_protected(base_path: Path) -> bool:
    """True if base_path is "/", the home dir, or any parent of the home dir.

    Guards against a misconfigured data/log/cache path: clearing it would wipe
    the whole disk or home directory.
    """
    resolved = base_path.resolve()
    return resolved == Path(resolved.anchor) or Path.home().resolve().is_relative_to(
        resolved
    )


def _empty_dir(path: Path) -> None:
    """Delete everything inside path, keep path itself.

    Unlike rmtree(path) + mkdir, this works when path is a symlink or a mount
    point, and keeps path's permissions. Symlinks inside are unlinked, not
    followed.
    """
    for item in path.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()


def _red(path: Path) -> str:
    return click.style(str(path), fg="red", bold=True)


def _remove_path(
    base_path: Path, target: str | None, path_name: str, yes: bool = False
) -> None:
    """Shared logic for clearing cache/data/log paths.

    Errors are raised as click.ClickException: Click prints "Error: ..." and
    exits 1, and pfund-shell catches it without leaving the shell.

    Args:
        base_path: The base directory path (e.g., config.cache_path)
        target: Optional target file/folder within base_path
        path_name: Display name for messages (e.g., "Cache", "Data", "Log")
        yes: Skip the confirmation prompt
    """
    # absolute (not resolved) so every message shows the full path the app uses
    base_path = Path(base_path).absolute()
    name = path_name.lower()

    # If no target specified, clear entire directory
    if not target:
        target_path = base_path
        clear_all = True
        if _is_protected(base_path):
            raise click.ClickException(
                f"{name} path is {base_path}, refusing to clear it (it is / or "
                f"contains your home directory). Fix the {name} path in your config."
            )
    else:
        # exact name only: never delete something the user didn't type
        target_path = base_path / target
        clear_all = False

        # Refuse anything that escapes base_path, e.g. "..", "../..", "/abs/path"
        # (pathlib drops base_path when joined with an absolute path).
        if not _is_inside(base_path, target_path):
            raise click.ClickException(
                f"'{target}' is outside {base_path}, refusing to remove it"
            )

    # Check if target exists (lexists so a dangling symlink can still be removed)
    if not os.path.lexists(target_path):
        if clear_all:
            # nothing to clear is not an error (like `rm -f`)
            click.echo(f"Nothing to clear, {base_path} does not exist.")
            return
        raise click.ClickException(f"'{target}' not found in {base_path}")
    if clear_all and not base_path.is_dir():
        raise click.ClickException(f"{base_path} is not a directory")

    # Last step before deleting: show the exact path and ask (default No)
    if not yes:
        if clear_all:
            question = f"Remove EVERYTHING in {_red(base_path)}"
            if base_path.is_symlink():
                question += f" (symlink to {_red(base_path.resolve())})"
            question += "?"
        elif target_path.is_symlink():
            question = f"Remove symlink {_red(target_path)} (not what it points to)?"
        else:
            question = f"Remove {_red(target_path)}?"
        if not _confirm(question):
            click.echo("Cancelled, nothing removed.")
            return

    try:
        # Clear the target
        if clear_all:
            click.echo(f"Emptying {name} directory: {base_path}")
            _empty_dir(base_path)
            click.echo(f"{path_name} directory cleared successfully!")
        elif target_path.is_symlink():
            # remove the link only, never what it points to
            click.echo(f"Removing symlink: {target_path}")
            target_path.unlink()
            click.echo(f"{path_name} symlink removed successfully!")
        elif target_path.is_file():
            click.echo(f"Removing file: {target_path}")
            target_path.unlink()
            click.echo(f"{path_name} file cleared successfully!")
        elif target_path.is_dir():
            click.echo(f"Removing folder: {target_path}")
            shutil.rmtree(target_path)
            click.echo(f"{path_name} folder cleared successfully!")
    except OSError as e:
        # filesystem errors (permission denied, busy, ...); anything else is a
        # bug and should surface with a traceback
        raise click.ClickException(f"failed clearing {name}: {e}") from e


_yes_option = click.option(
    "--yes", "-y", is_flag=True, help="Skip the confirmation prompt."
)


@remove.command()
@click.pass_context
@click.argument("target", type=str, required=False)
@_yes_option
def cache(ctx: click.Context, target: str | None, yes: bool) -> None:
    """Remove cache directory or specific cache files/folders.

    \b
    Examples:
        remove cache              # Empty the cache directory (asks first)
        remove cache api          # Remove cache/api folder
        remove cache models.pkl   # Remove cache/models.pkl file
        remove cache api -y       # Same, without asking
    """
    _remove_path(ctx.obj["config"].cache_path, target, "Cache", yes=yes)


@remove.command()
@click.pass_context
@click.argument("target", type=str, required=False)
@_yes_option
def data(ctx: click.Context, target: str | None, yes: bool) -> None:
    """Remove data directory or specific data files/folders.

    \b
    Examples:
        remove data               # Empty the data directory (asks first)
        remove data some_folder   # Remove data/some_folder folder
        remove data backup.db     # Remove data/backup.db file
        remove data backup.db -y  # Same, without asking
    """
    _remove_path(ctx.obj["config"].data_path, target, "Data", yes=yes)


@remove.command()
@click.pass_context
@click.argument("target", type=str, required=False)
@_yes_option
def log(ctx: click.Context, target: str | None, yes: bool) -> None:
    """Remove log directory or specific log files/folders. Alias: logs.

    \b
    Examples:
        remove log                # Empty the log directory (asks first)
        remove log app            # Remove logs/app folder
        remove log error.log      # Remove logs/error.log file
        remove log app -y         # Same, without asking
    """
    _remove_path(ctx.obj["config"].log_path, target, "Log", yes=yes)


# the directory is named "logs" (see paths.py), so accept that too
remove.add_command(log, name="logs")
