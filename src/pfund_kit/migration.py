from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from packaging.version import Version


__all__ = ["Migration", "migrate"]


Migration = Callable[[dict[str, Any]], dict[str, Any]]
"""Takes a file's fields (without ``__version__``) and returns the upgraded fields."""


def migrate(
    data: dict[str, Any],
    *,
    target: str,
    migrations: dict[str, tuple[str, Migration]],
    name: str = "Settings",
) -> dict[str, Any]:
    """Upgrade a versioned file's data to ``target`` and return its fields.

    ``data`` must carry ``__version__``. Each step is looked up as
    ``migrations[version] == (next_version, function)`` and must strictly
    advance towards ``target`` without overshooting it. A version newer than
    ``target`` is refused, so an older package never rewrites a newer file.
    The returned dict never contains ``__version__``; the caller adds the
    target version when writing. ``name`` only labels error messages.
    """
    data = copy.deepcopy(data)
    if "__version__" not in data:
        raise ValueError(f"{name} file is missing __version__")
    version = data.pop("__version__", None)
    if not isinstance(version, str):
        raise ValueError(f"{name} __version__ must be a version string")
    target_version = Version(target)
    if Version(version) > target_version:
        raise ValueError(f"{name} version {version} is newer than supported {target}")
    label = name.lower()
    while Version(version) < target_version:
        transition = migrations.get(version)
        if transition is None:
            raise ValueError(f"No {label} migration from {version} to {target}")
        next_version, function = transition
        if not Version(version) < Version(next_version) <= target_version:
            raise ValueError(f"Invalid {label} migration: {version} -> {next_version}")
        data = function(data)
        if not isinstance(data, dict) or "__version__" in data:
            raise ValueError(f"A {label} migration must return fields without __version__")
        version = next_version
    return data
