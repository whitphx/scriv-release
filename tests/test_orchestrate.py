from __future__ import annotations

import subprocess
from typing import Any

import pytest

from scriv_release import orchestrate
from scriv_release.config import Config


def test_parse_marker_basic() -> None:
    body = "Some text\n\nscriv-release-bump: minor\n\nMore text\n"
    assert orchestrate.parse_marker(body, key="scriv-release-bump") == "minor"


def test_parse_marker_case_insensitive_value() -> None:
    body = "scriv-release-bump: MAJOR"
    assert orchestrate.parse_marker(body, key="scriv-release-bump") == "major"


def test_parse_marker_indented() -> None:
    body = "  scriv-release-bump: patch  "
    assert orchestrate.parse_marker(body, key="scriv-release-bump") == "patch"


def test_parse_marker_absent() -> None:
    assert orchestrate.parse_marker("nothing here", key="scriv-release-bump") is None


def test_parse_marker_wrong_key() -> None:
    body = "other-marker: minor"
    assert orchestrate.parse_marker(body, key="scriv-release-bump") is None


def test_parse_marker_invalid_value() -> None:
    body = "scriv-release-bump: huge"
    assert orchestrate.parse_marker(body, key="scriv-release-bump") is None


def test_parse_marker_custom_key() -> None:
    body = "release-kind: major"
    assert orchestrate.parse_marker(body, key="release-kind") == "major"


def _stub_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[list[str]], dict[tuple[str, ...], tuple[int, str]]]:
    calls: list[list[str]] = []
    responses: dict[tuple[str, ...], tuple[int, str]] = {}

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        rc, out = responses.get(tuple(args), (0, ""))
        check = kwargs.get("check", False)
        if check and rc != 0:
            raise subprocess.CalledProcessError(rc, args, out, "")
        return subprocess.CompletedProcess(args, rc, out, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls, responses


def test_detect_release_marker_mode_uses_pr_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    calls, responses = _stub_subprocess(monkeypatch)
    responses[("git", "rev-parse", "HEAD")] = (0, "abc123\n")
    responses[
        (
            "gh",
            "api",
            "/repos/owner/repo/commits/abc123/pulls",
            "--jq",
            ".[0].body // empty",
        )
    ] = (0, "scriv-release-bump: minor\n")

    config = Config(release_detection="pr-body-marker")
    assert orchestrate.detect_release(config=config) == "minor"
    assert calls[0] == ["git", "rev-parse", "HEAD"]
    assert calls[1][0] == "gh"


def test_detect_release_marker_mode_returns_none_when_marker_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    _, responses = _stub_subprocess(monkeypatch)
    responses[("git", "rev-parse", "HEAD")] = (0, "abc123\n")
    responses[
        (
            "gh",
            "api",
            "/repos/owner/repo/commits/abc123/pulls",
            "--jq",
            ".[0].body // empty",
        )
    ] = (0, "PR with no marker\n")

    config = Config(release_detection="pr-body-marker")
    assert orchestrate.detect_release(config=config) is None


def test_detect_release_auto_falls_back_to_history_when_no_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    _, responses = _stub_subprocess(monkeypatch)
    responses[("git", "rev-parse", "HEAD")] = (0, "abc123\n")
    responses[
        (
            "gh",
            "api",
            "/repos/owner/repo/commits/abc123/pulls",
            "--jq",
            ".[0].body // empty",
        )
    ] = (0, "")

    history_called = {"value": False}

    def fake_history() -> str | None:
        history_called["value"] = True
        return "patch"

    monkeypatch.setattr(orchestrate, "_detect_via_fragment_history", fake_history)

    config = Config(release_detection="auto")
    assert orchestrate.detect_release(config=config) == "patch"
    assert history_called["value"] is True


def test_detect_release_history_mode_skips_pr_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _ = _stub_subprocess(monkeypatch)

    def fake_history() -> str | None:
        return "minor"

    monkeypatch.setattr(orchestrate, "_detect_via_fragment_history", fake_history)

    config = Config(release_detection="history")
    assert orchestrate.detect_release(config=config) == "minor"
    assert all(c[0] != "gh" for c in calls)


def test_detect_release_marker_mode_no_repo_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    calls, _ = _stub_subprocess(monkeypatch)

    config = Config(release_detection="pr-body-marker")
    assert orchestrate.detect_release(config=config) is None
    assert all(c[0] != "gh" for c in calls)
