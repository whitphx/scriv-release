from __future__ import annotations

import subprocess
from typing import Any

import pytest

from scriv_release.versioning import _git


def _capture_runs(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_finalize_tag_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_runs(monkeypatch)
    _git.finalize("1.2.3", tag=True, commit=False, push=False)
    assert calls == [["git", "tag", "v1.2.3"]]


def test_finalize_commit_tag_push(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_runs(monkeypatch)
    _git.finalize("1.2.3", tag=True, commit=True, push=True)
    assert calls == [
        ["git", "add", "-A"],
        ["git", "commit", "-m", "Release v1.2.3"],
        ["git", "tag", "v1.2.3"],
        ["git", "push", "--follow-tags"],
    ]


def test_finalize_custom_tag_format(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_runs(monkeypatch)
    _git.finalize(
        "1.2.3", tag=True, commit=False, push=False, tag_format="rel-{version}"
    )
    assert calls == [["git", "tag", "rel-1.2.3"]]


def test_finalize_no_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_runs(monkeypatch)
    _git.finalize("1.2.3", tag=False, commit=False, push=False)
    assert calls == []
