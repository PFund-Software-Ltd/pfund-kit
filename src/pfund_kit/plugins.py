"""Plugin discovery via entry points, shared by the pfund ecosystem.

A plugin package registers an entry point named after the plugin, under its host's group, e.g.:
    [project.entry-points."pfeed.sources"]
    bybit = "pfeed_bybit:Bybit"

Names are case-insensitive and stored uppercased.
Domain checks on the loaded object (e.g. its name matches the entry point) belong to the host package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint

from importlib import import_module
from importlib.metadata import entry_points

__all__ = ["PluginRegistry", "import_official_plugin"]


class PluginRegistry:
    """Registry of the plugins installed under one entry point group.

    Args:
        group: entry point group, e.g. "pfeed.sources".
        kind: what a plugin is called in error messages, e.g. "data source".
    """

    def __init__(self, group: str, kind: str = "plugin"):
        self.group = group
        self.kind = kind
        self._entry_points: dict[str, EntryPoint] | None = None

    def get_entry_points(self) -> dict[str, EntryPoint]:
        """Returns {plugin name: entry point} of all installed plugins, without importing them."""
        if self._entry_points is None:
            eps: dict[str, EntryPoint] = {}
            for ep in entry_points(group=self.group):
                name = ep.name.upper()
                if name in eps:
                    dists = [e.dist.name if e.dist else "unknown" for e in (eps[name], ep)]
                    raise ValueError(f"{self.kind} {name} is registered by multiple packages: {dists}")
                eps[name] = ep
            self._entry_points = eps
        return self._entry_points

    def cache_clear(self) -> None:
        """Forgets the discovered entry points, e.g. after installing a plugin at runtime."""
        self._entry_points = None

    def list_names(self) -> list[str]:
        return sorted(self.get_entry_points())

    def get_entry_point(self, name: str) -> EntryPoint:
        try:
            return self.get_entry_points()[name.upper()]
        except KeyError:
            raise ValueError(
                f"unknown {self.kind} '{name}', installed {self.kind}s: {self.list_names()}"
            ) from None

    def load(self, name: str) -> Any:
        return self.get_entry_point(name).load()


def import_official_plugin(module: str, attr: str, *, label: str = "", install: str = "") -> Any:
    """Imports `attr` from an official plugin's `module`, with an install hint if the plugin is missing.

    Args:
        module: the plugin's module, e.g. "pfeed_bybit".
        attr: the object to import from it, e.g. "Bybit".
        label: how the caller refers to it in the error, e.g. "pe.Bybit". Defaults to `attr`.
        install: what to pip install, e.g. "pfund[bybit]". Defaults to the plugin's package name.
    """
    try:
        return getattr(import_module(module), attr)
    except ModuleNotFoundError as err:
        # only rewrite the error if the plugin itself is missing, not a broken import inside it
        if err.name != module:
            raise
        package = module.replace("_", "-")
        raise ModuleNotFoundError(
            f"{label or attr} requires the official plugin '{package}', "
            + f"install it with: pip install {install or package}",
            name=err.name,
        ) from err
