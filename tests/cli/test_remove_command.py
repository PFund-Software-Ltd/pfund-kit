from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from pfund_kit.cli.commands.remove import remove


@pytest.fixture
def layout(tmp_path: Path) -> SimpleNamespace:
    """~/.proj-like layout: user_root/{data,cache,logs} plus a sibling outside it."""
    user_root = tmp_path / ".proj"
    data = user_root / "data"
    (data / "subdir").mkdir(parents=True)
    (data / "backup.db").write_text("db")
    (user_root / "cache").mkdir()
    (user_root / "logs").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    config = SimpleNamespace(
        data_path=data,
        cache_path=user_root / "cache",
        log_path=user_root / "logs",
    )
    return SimpleNamespace(
        user_root=user_root, data=data, outside=outside, config=config
    )


def _run(layout: SimpleNamespace, *args: str, input: str | None = None):
    return CliRunner().invoke(
        remove, list(args), obj={"config": layout.config}, input=input
    )


@pytest.mark.parametrize(
    "target",
    ["..", "../..", "../../outside", "subdir/../..", ".", "subdir/.."],
)
def test_rejects_relative_escape(layout: SimpleNamespace, target: str) -> None:
    result = _run(layout, "data", target)
    assert result.exit_code == 1
    assert "outside" in result.output
    assert layout.user_root.exists()
    assert (layout.data / "subdir").exists()
    assert (layout.outside / "keep.txt").exists()


def test_rejects_absolute_path(layout: SimpleNamespace) -> None:
    result = _run(layout, "data", str(layout.outside))
    assert result.exit_code == 1
    assert (layout.outside / "keep.txt").exists()


def test_symlink_removes_link_not_target(layout: SimpleNamespace) -> None:
    link = layout.data / "ext"
    link.symlink_to(layout.outside, target_is_directory=True)
    result = _run(layout, "data", "ext", "--yes")
    assert result.exit_code == 0, result.output
    assert not link.exists() and not link.is_symlink()
    assert (layout.outside / "keep.txt").exists()


def test_rejects_path_through_symlink_escaping(layout: SimpleNamespace) -> None:
    (layout.data / "ext").symlink_to(layout.outside, target_is_directory=True)
    result = _run(layout, "data", "ext/keep.txt")
    assert result.exit_code == 1
    assert (layout.outside / "keep.txt").exists()


def test_removes_file_and_folder_inside(layout: SimpleNamespace) -> None:
    assert _run(layout, "data", "backup.db", "-y").exit_code == 0
    assert not (layout.data / "backup.db").exists()
    assert _run(layout, "data", "subdir", "-y").exit_code == 0
    assert not (layout.data / "subdir").exists()


def test_clear_all_recreates_empty_dir(layout: SimpleNamespace) -> None:
    result = _run(layout, "data", "--yes")
    assert result.exit_code == 0, result.output
    assert layout.data.is_dir()
    assert not any(layout.data.iterdir())
    assert (layout.outside / "keep.txt").exists()


# --- confirmation prompt ---


@pytest.mark.parametrize("answer", ["n\n", "\n", ""], ids=["no", "enter", "eof"])
def test_prompt_declined_removes_nothing(layout: SimpleNamespace, answer: str) -> None:
    result = _run(layout, "data", "backup.db", input=answer)
    assert result.exit_code == 0, result.output
    assert f"Remove {layout.data / 'backup.db'}?" in result.output
    assert "Cancelled, nothing removed." in result.output
    assert (layout.data / "backup.db").exists()


def test_prompt_yes_removes(layout: SimpleNamespace) -> None:
    result = _run(layout, "data", "backup.db", input="y\n")
    assert result.exit_code == 0, result.output
    assert not (layout.data / "backup.db").exists()


def test_clear_all_prompt_declined(layout: SimpleNamespace) -> None:
    result = _run(layout, "data", input="n\n")
    assert result.exit_code == 0, result.output
    assert f"Remove EVERYTHING in {layout.data}?" in result.output
    assert (layout.data / "subdir").exists()
    assert (layout.data / "backup.db").exists()


def test_symlink_prompt_says_link_only(layout: SimpleNamespace) -> None:
    (layout.data / "ext").symlink_to(layout.outside, target_is_directory=True)
    result = _run(layout, "data", "ext", input="n\n")
    assert "(not what it points to)" in result.output
    assert (layout.data / "ext").is_symlink()


def test_refused_or_missing_target_never_prompts(layout: SimpleNamespace) -> None:
    for target in ("..", "nope"):
        result = _run(layout, "data", target)
        assert result.exit_code == 1
        assert "?" not in result.output


# --- clear-all: protected base paths, emptying, absolute + red paths ---


def _run_base(base: Path, *args: str, input: str | None = None, color: bool = False):
    config = SimpleNamespace(data_path=base, cache_path=base, log_path=base)
    return CliRunner().invoke(
        remove, ["data", *args], obj={"config": config}, input=input, color=color
    )


@pytest.mark.parametrize("which", ["home", "parent_of_home", "root"])
def test_clear_all_refuses_protected_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    home = tmp_path / "home" / "me"
    home.mkdir(parents=True)
    (home / "keep.txt").write_text("keep")
    monkeypatch.setenv("HOME", str(home))
    base = {"home": home, "parent_of_home": home.parent, "root": Path("/")}[which]
    result = _run_base(base, "--yes")
    assert result.exit_code == 1
    assert "refusing to clear" in result.output
    assert (home / "keep.txt").exists()


def test_clear_all_keeps_dir_and_its_permissions(layout: SimpleNamespace) -> None:
    layout.data.chmod(0o700)
    result = _run(layout, "data", "--yes")
    assert result.exit_code == 0, result.output
    assert layout.data.is_dir()
    assert not any(layout.data.iterdir())
    assert layout.data.stat().st_mode & 0o777 == 0o700


def test_clear_all_unlinks_inner_symlinks_without_following(
    layout: SimpleNamespace,
) -> None:
    (layout.data / "ext").symlink_to(layout.outside, target_is_directory=True)
    result = _run(layout, "data", "--yes")
    assert result.exit_code == 0, result.output
    assert not any(layout.data.iterdir())
    assert (layout.outside / "keep.txt").exists()


def test_clear_all_symlinked_base_empties_target_keeps_link(tmp_path: Path) -> None:
    real = tmp_path / "ssd" / "data"
    (real / "sub").mkdir(parents=True)
    (real / "a.db").write_text("x")
    link = tmp_path / "data"
    link.symlink_to(real, target_is_directory=True)

    declined = _run_base(link, input="n\n")
    assert f"Remove EVERYTHING in {link} (symlink to {real.resolve()})?" in (
        declined.output
    )
    assert (real / "a.db").exists()

    result = _run_base(link, "--yes")
    assert result.exit_code == 0, result.output
    assert link.is_symlink()
    assert real.is_dir()
    assert not any(real.iterdir())


def test_clear_all_base_is_a_file(tmp_path: Path) -> None:
    f = tmp_path / "data"
    f.write_text("x")
    result = _run_base(f, "--yes")
    assert result.exit_code == 1
    assert "is not a directory" in result.output
    assert f.exists()


def test_relative_base_is_shown_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.db").write_text("x")
    result = _run_base(Path("data"), "a.db", input="n\n")
    assert f"Remove {tmp_path.absolute() / 'data' / 'a.db'}?" in result.output


def test_prompt_path_is_bold_red(layout: SimpleNamespace) -> None:
    result = _run_base(layout.data, "backup.db", input="n\n", color=True)
    styled = click.style(str(layout.data / "backup.db"), fg="red", bold=True)
    assert f"Remove {styled}?" in result.output
    assert "\x1b[31m" in styled and "\x1b[1m" in styled


def test_no_case_insensitive_fallback(layout: SimpleNamespace) -> None:
    # macOS/Windows filesystems are case-insensitive, so "BACKUP.DB" really is
    # backup.db there; on Linux it must NOT fall back to backup.db.
    case_insensitive = (layout.data / "BACKUP.DB").exists()
    result = _run(layout, "data", "BACKUP.DB", input="n\n")
    assert "case-insensitive" not in result.output
    if not case_insensitive:
        assert result.exit_code == 1
        assert "not found" in result.output
    assert (layout.data / "backup.db").exists()


# --- #6: ClickException errors, missing base, no logs alias, help text ---


def test_errors_are_click_exceptions(layout: SimpleNamespace) -> None:
    result = _run(layout, "data", "nope")
    assert result.exit_code == 1
    assert result.output.startswith("Error: 'nope' not found in ")


def test_clear_all_missing_base_is_not_an_error(tmp_path: Path) -> None:
    result = _run_base(tmp_path / "missing", "--yes")
    assert result.exit_code == 0, result.output
    assert "Nothing to clear" in result.output
    assert not (tmp_path / "missing").exists()  # not created either


def test_filesystem_error_becomes_click_error(layout: SimpleNamespace) -> None:
    layout.data.chmod(0o500)  # can't delete entries inside
    try:
        result = _run(layout, "data", "backup.db", "--yes")
    finally:
        layout.data.chmod(0o700)
    assert result.exit_code == 1
    assert "Error: failed clearing data:" in result.output
    assert (layout.data / "backup.db").exists()


def test_logs_is_not_an_alias(layout: SimpleNamespace) -> None:
    """Only `log` exists, so the shell menu shows one name."""
    (layout.config.log_path / "app.log").write_text("x")
    result = _run(layout, "logs", "app.log", "--yes")
    assert result.exit_code == 2
    assert "No such command 'logs'" in result.output
    assert (layout.config.log_path / "app.log").exists()


def test_help_examples_are_not_rewrapped_or_pfeed_specific(
    layout: SimpleNamespace,
) -> None:
    result = _run(layout, "data", "--help")
    assert "pfeed" not in result.output
    assert "\n      remove data backup.db -y  # Same, without asking\n" in result.output
