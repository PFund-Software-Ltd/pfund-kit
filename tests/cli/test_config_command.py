from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from pfund_kit.cli.commands.config import config as config_group


class _FakeConfig:
    filename = "config.yaml"

    def __init__(self) -> None:
        self.data_path: Path | None = None
        self.saved = False

    def save(self) -> None:
        self.saved = True


@pytest.mark.parametrize("arg", ["~/mydata", "'~/mydata'"])
def test_config_set_expands_tilde_even_if_quoted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arg: str
) -> None:
    # CliRunner passes args without a shell, so "~" arrives unexpanded,
    # exactly like a quoted '~/mydata' typed in a real shell.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    cfg = _FakeConfig()
    result = CliRunner().invoke(
        config_group, ["set", "--data", arg.strip("'")], obj={"config": cfg}
    )
    assert result.exit_code == 0, result.output
    assert cfg.data_path == (tmp_path / "home" / "mydata").resolve()
    assert cfg.saved
    assert not (tmp_path / "~").exists()


def test_config_set_resolves_relative_against_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = _FakeConfig()
    result = CliRunner().invoke(
        config_group, ["set", "--data", "data"], obj={"config": cfg}
    )
    assert result.exit_code == 0, result.output
    assert cfg.data_path == (tmp_path / "data").resolve()
    assert cfg.data_path.is_absolute()
