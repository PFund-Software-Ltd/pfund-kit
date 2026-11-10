from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

import click
import pytest

from pfund_kit.pfund_shell import main


def _make_group(name: str, calls: list[str]) -> click.Group:
    """A project group with a shared `remove data` and its own `download`."""

    @click.group(name=name)
    def group() -> None:
        pass

    @group.group(name="remove")
    def remove() -> None:
        pass

    @remove.command(name="data")
    def data() -> None:
        calls.append(f"{name} remove data")

    @group.command(name="download")
    def download() -> None:
        calls.append(f"{name} download")

    return group


@pytest.fixture
def run_shell(mocker: MockerFixture):
    """Feed lines into start_shell, return (calls, output)."""

    def _run(lines: list[str], capsys: pytest.CaptureFixture[str]):
        calls: list[str] = []
        groups = {"pfeed": _make_group("pfeed", calls)}
        groups["pfund"] = _make_group("pfund", calls)
        mocker.patch.object(main, "discover_command_groups", return_value=groups)
        session = mocker.patch.object(main, "PromptSession").return_value
        session.prompt.side_effect = [*lines, EOFError]
        main.start_shell()
        return calls, capsys.readouterr().out

    return _run


@pytest.mark.parametrize("line", ["remove data", "rm data", "config", "remove"])
def test_shared_command_at_root_is_refused(
    run_shell, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    calls, out = run_shell([line], capsys)
    assert calls == []  # nothing ran in ANY project
    assert "is per-project, which one?" in out
    assert f"'pfeed {line}' / 'pfund {line}'" in out


def test_explicit_project_prefix_runs_only_that_project(
    run_shell, capsys: pytest.CaptureFixture[str]
) -> None:
    calls, _ = run_shell(["pfund remove data"], capsys)
    assert calls == ["pfund remove data"]


def test_inside_project_context_runs_that_project(
    run_shell, capsys: pytest.CaptureFixture[str]
) -> None:
    calls, _ = run_shell(["pfund", "remove data"], capsys)
    assert calls == ["pfund remove data"]


def test_non_shared_root_command_still_routes(
    run_shell, capsys: pytest.CaptureFixture[str]
) -> None:
    calls, _ = run_shell(["download"], capsys)
    assert calls == ["pfeed download"]


# --- autocomplete offers only the alias when a command has one ---


@pytest.fixture
def complete():
    from prompt_toolkit.document import Document

    from pfund_kit.cli.commands.remove import remove
    from pfund_kit.pfund_shell.shell_group import create_pfund_shell_group

    @click.group()
    def pfeed() -> None:
        pass

    pfeed.add_command(remove)
    pfeed.add_command(remove, "rm")
    groups = {"pfeed": pfeed}
    completer = main.get_completer(groups, create_pfund_shell_group(groups), "pfeed")

    def _complete(text: str) -> list[str]:
        return sorted(c.text for c in completer.get_completions(Document(text), None))

    return _complete


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ["rm"]),
        ("r", ["rm"]),
        ("rm ", ["cache", "data", "log"]),
        ("rm lo", ["log"]),
        ("remove ", []),  # full name is hidden (still runs if typed)
    ],
)
def test_autocomplete_offers_only_aliases(
    complete, text: str, expected: list[str]
) -> None:
    assert complete(text) == expected


PFEED_COMMANDS = [
    "tui", "config", "docker-compose", "compose", "remove", "rm",
    "ducklake", "data", "download", "stream",
]  # fmt: skip


@pytest.mark.parametrize("line_width", [20, 40, 80, 110, 116, 200])
def test_commands_menu_fits_width(line_width: int) -> None:
    """Every row fits the terminal (the toolbar truncates, never wraps)."""
    from pfund_kit.pfund_shell.toolbar import format_commands_menu

    menu = format_commands_menu(PFEED_COMMANDS, width=12, line_width=line_width)
    rows = menu.split("\n")
    assert all(len(row) <= line_width for row in rows)
    # nothing dropped or cut, in order
    assert " ".join(rows).split() == PFEED_COMMANDS


def test_commands_menu_aligned_columns() -> None:
    """A long name (docker-compose) widens every column instead of shifting."""
    from pfund_kit.pfund_shell.toolbar import format_commands_menu

    rows = format_commands_menu(PFEED_COMMANDS, width=12, line_width=110).split("\n")
    # col width 14 -> 7 per row (7*14 + 6 = 104 <= 110)
    assert rows[0].split() == PFEED_COMMANDS[:7]
    assert rows[1].index("download") == 15  # second column starts at 14 + 1


def test_commands_menu_narrower_than_one_column() -> None:
    from pfund_kit.pfund_shell.toolbar import format_commands_menu

    assert format_commands_menu(["download", "stream"], width=12, line_width=5) == (
        "download\nstream"
    )
    assert format_commands_menu([], width=12, line_width=80) == ""


def _add_tui():
    """Replacement for _make_group: each project also has a `tui` command."""
    original = _make_group  # bound now, before the patch replaces the global

    def make(name: str, calls: list[str]) -> click.Group:
        group = original(name, calls)

        @group.command(name="tui")
        def tui() -> None:
            calls.append(f"{name} tui")

        return group

    return make


@pytest.mark.parametrize(
    ("lines", "hint"),
    [
        (["tui"], "pfeed tui"),
        (["pfund tui"], "pfund tui"),
        (["pfund", "tui"], "pfund tui"),
    ],
)
def test_tui_is_disabled_in_shell(
    mocker: MockerFixture,
    run_shell,
    capsys: pytest.CaptureFixture[str],
    lines: list[str],
    hint: str,
) -> None:
    mocker.patch(f"{__name__}._make_group", _add_tui())
    calls, out = run_shell(lines, capsys)
    assert calls == []
    assert f"'tui' is not available in pfund-shell, run '{hint}'" in out


def test_tui_not_offered_in_completion_or_toolbar() -> None:
    from pfund_kit.pfund_shell.shell_group import create_pfund_shell_group
    from pfund_kit.pfund_shell.utils import get_commands_dict

    groups = {"pfeed": _add_tui()("pfeed", [])}
    shell_group = create_pfund_shell_group(groups)
    root = get_commands_dict(groups, shell_group, "pfund-shell")
    inside = get_commands_dict(groups, shell_group, "pfeed")
    assert "tui" not in root and "tui" not in root["pfeed"]
    assert "tui" not in inside
    assert "download" in inside  # other commands untouched


def test_full_name_still_runs_when_alias_is_shown() -> None:
    from pfund_kit.cli.commands.remove import remove
    from pfund_kit.pfund_shell.utils import shell_commands

    @click.group()
    def pfeed() -> None:
        pass

    pfeed.add_command(remove)
    pfeed.add_command(remove, "rm")
    assert [name for name, _ in shell_commands(pfeed)] == ["rm"]
    # hidden from the menu, but Click still resolves it
    assert pfeed.get_command(click.Context(pfeed), "remove") is remove
