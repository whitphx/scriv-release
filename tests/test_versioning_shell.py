from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from scriv_release.versioning.shell import Provider


def _write_pyproject(tmp_path: Path, body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")


def test_current_runs_configured_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.scriv-release.shell]
current = "echo 1.2.3"
apply = "true"
""",
    )
    monkeypatch.chdir(tmp_path)
    assert Provider().current() == "1.2.3"


def test_next_falls_back_to_packaging_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.scriv-release.shell]
current = "echo 1.2.3"
apply = "true"
""",
    )
    monkeypatch.chdir(tmp_path)
    assert Provider().next("minor") == "1.3.0"


def test_next_uses_configured_command_with_level_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.scriv-release.shell]
current = "echo 1.2.3"
next = "echo bumped-$LEVEL"
apply = "true"
""",
    )
    monkeypatch.chdir(tmp_path)
    assert Provider().next("major") == "bumped-major"


def test_apply_runs_apply_command_then_finalizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.scriv-release.shell]
current = "echo 1.2.3"
apply = "echo applied:$LEVEL:$NEW_VERSION > apply.log"
""",
    )
    monkeypatch.chdir(tmp_path)

    git_calls: list[list[str]] = []
    real_run = subprocess.run

    def spy_run(args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if isinstance(args, list) and args and args[0] == "git":
            git_calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy_run)

    new_version = Provider().apply("patch", tag=True, commit=False, push=False)
    assert new_version == "1.2.4"
    assert (tmp_path / "apply.log").read_text().strip() == "applied:patch:1.2.4"
    assert git_calls == [["git", "tag", "v1.2.4"]]


def test_missing_required_command_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject(tmp_path, "[tool.scriv-release.shell]\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="current"):
        Provider().current()
