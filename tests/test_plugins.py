"""Tests pfund_kit.plugins against fake entry points, so no real plugin has to be installed."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

import sys
import types
from importlib.metadata import EntryPoint

import pytest

from pfund_kit import plugins
from pfund_kit.plugins import PluginRegistry, import_official_plugin

GROUP = "fake.plugins"
FAKE_MODULE = "fake_plugin"


class FakePlugin:
    pass


def _ep(name: str, group: str = GROUP) -> EntryPoint:
    return EntryPoint(name=name, value=f"{FAKE_MODULE}:FakePlugin", group=group)


@pytest.fixture
def registry() -> PluginRegistry:
    return PluginRegistry(GROUP, kind="widget")


@pytest.fixture
def install_plugins(mocker: MockerFixture) -> Callable[..., None]:
    """Replaces the installed entry points with the given fake ones."""
    module = types.ModuleType(FAKE_MODULE)
    setattr(module, "FakePlugin", FakePlugin)  # noqa: B010
    mocker.patch.dict(sys.modules, {FAKE_MODULE: module})

    def _install(*eps: EntryPoint) -> None:
        mocker.patch.object(plugins, "entry_points", lambda group: [ep for ep in eps if ep.group == group])

    return _install


def test_names_are_uppercased(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"))
    assert list(registry.get_entry_points()) == ["FAKE"]


def test_only_own_group_is_discovered(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"), _ep("other", group="other.plugins"))
    assert registry.list_names() == ["FAKE"]


def test_duplicate_names_raise(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"), _ep("FAKE"))
    with pytest.raises(ValueError, match="widget FAKE is registered by multiple packages"):
        registry.get_entry_points()


def test_list_names_is_sorted(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("zeta"), _ep("alpha"))
    assert registry.list_names() == ["ALPHA", "ZETA"]


def test_no_plugins_installed(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins()
    assert registry.list_names() == []
    with pytest.raises(ValueError, match="unknown widget 'fake'"):
        registry.load("fake")


def test_get_entry_point_is_case_insensitive(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"))
    assert registry.get_entry_point("Fake").name == "fake"


def test_get_entry_point_unknown(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"))
    with pytest.raises(ValueError, match=r"unknown widget 'nope', installed widgets: \['FAKE'\]"):
        registry.get_entry_point("nope")


def test_load(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"))
    assert registry.load("fake") is FakePlugin


def test_entry_points_are_cached_until_cleared(registry: PluginRegistry, install_plugins: Callable[..., None]):
    install_plugins(_ep("fake"))
    assert registry.list_names() == ["FAKE"]
    install_plugins(_ep("fake"), _ep("new"))
    assert registry.list_names() == ["FAKE"]
    registry.cache_clear()
    assert registry.list_names() == ["FAKE", "NEW"]


def test_import_official_plugin(install_plugins: Callable[..., None]):
    assert import_official_plugin(FAKE_MODULE, "FakePlugin") is FakePlugin


def test_import_official_plugin_missing_plugin_has_install_hint():
    with pytest.raises(ModuleNotFoundError, match=r"pe\.Missing requires the official plugin 'not-installed-plugin', install it with: pip install host\[missing\]"):
        import_official_plugin("not_installed_plugin", "Missing", label="pe.Missing", install="host[missing]")


def test_import_official_plugin_defaults_to_package_name():
    with pytest.raises(ModuleNotFoundError, match=r"Missing requires .* pip install not-installed-plugin$"):
        import_official_plugin("not_installed_plugin", "Missing")


def test_import_official_plugin_keeps_broken_import_inside_plugin(mocker: MockerFixture):
    err = ModuleNotFoundError("No module named 'some_dep'", name="some_dep")
    mocker.patch.object(plugins, "import_module", side_effect=err)
    with pytest.raises(ModuleNotFoundError) as exc_info:
        import_official_plugin("fake_plugin", "FakePlugin")
    assert exc_info.value is err
