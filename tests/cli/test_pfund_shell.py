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


# --- autocomplete offers aliases (Click registers them as extra keys) ---


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
        ("", ["remove", "rm"]),
        ("remove ", ["cache", "data", "log", "logs"]),
        ("remove lo", ["log", "logs"]),
        ("rm ", ["cache", "data", "log", "logs"]),
    ],
)
def test_autocomplete_offers_aliases(complete, text: str, expected: list[str]) -> None:
    assert complete(text) == expected
