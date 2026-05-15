from __future__ import annotations

import subprocess
from typing import Any

import pytest

from scriv_release.versioning.bump_my_version import Provider


def _stub_subprocess(
    monkeypatch: pytest.MonkeyPatch, responses: dict[tuple[str, ...], str]
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        stdout = responses.get(tuple(args), "")
        return subprocess.CompletedProcess(args, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_current(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_subprocess(
        monkeypatch, {("bump-my-version", "show", "current_version"): "1.2.3\n"}
    )
    assert Provider().current() == "1.2.3"


def test_next(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_subprocess(
        monkeypatch,
        {
            (
                "bump-my-version",
                "show",
                "--increment",
                "minor",
                "new_version",
            ): "1.3.0\n",
        },
    )
    assert Provider().next("minor") == "1.3.0"


def test_apply_passes_allow_dirty(monkeypatch: pytest.MonkeyPatch) -> None:
    # collect_for_release leaves CHANGELOG.md modified and the consumed
    # fragment deleted before this provider runs, so we must pass
    # --allow-dirty or bump-my-version will refuse.
    calls = _stub_subprocess(
        monkeypatch,
        {("bump-my-version", "show", "current_version"): "1.2.4\n"},
    )
    Provider().apply("patch", tag=False, commit=False, push=False)
    bump_call = next(c for c in calls if c[:2] == ["bump-my-version", "bump"])
    assert "--allow-dirty" in bump_call


def test_apply_forwards_tag_and_commit_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_subprocess(
        monkeypatch,
        {("bump-my-version", "show", "current_version"): "1.2.4\n"},
    )
    Provider().apply("patch", tag=True, commit=True, push=False)
    bump_call = next(c for c in calls if c[:2] == ["bump-my-version", "bump"])
    assert "--tag" in bump_call
    assert "--no-commit" not in bump_call
