from __future__ import annotations

import subprocess
from typing import Any

import pytest

from scriv_release.versioning.uv import Provider


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
    _stub_subprocess(monkeypatch, {("uv", "version", "--short"): "1.2.3\n"})
    assert Provider().current() == "1.2.3"


def test_next(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_subprocess(
        monkeypatch,
        {("uv", "version", "--bump", "minor", "--dry-run", "--short"): "1.3.0\n"},
    )
    assert Provider().next("minor") == "1.3.0"


def test_apply_invokes_uv_then_finalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_subprocess(
        monkeypatch,
        {("uv", "version", "--bump", "patch", "--short", "--frozen"): "1.2.4\n"},
    )
    new_version = Provider().apply("patch", tag=True, commit=False, push=False)
    assert new_version == "1.2.4"
    assert calls == [
        ["uv", "version", "--bump", "patch", "--short", "--frozen"],
        ["git", "tag", "v1.2.4"],
    ]
