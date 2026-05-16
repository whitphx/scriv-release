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


_SCRIV_MD = """\
[tool.scriv]
categories = ["Added", "Fixed"]
format = "md"
md_header_level = 2
"""

_CHANGELOG_WITH_065 = """\
# Changelog

<!-- scriv-insert-here -->

<a id='changelog-0.65.1'></a>
## 0.65.1 — 2026-05-04

### Chore

- Migrate the changelog/release workflow to the scriv-release reusable workflow.

<a id='changelog-0.65.0'></a>
## 0.65.0 — 2026-04-20

### Added

- Initial.
"""


def _setup_scriv_repo(tmp_path: Any, changelog_text: str) -> None:
    (tmp_path / "pyproject.toml").write_text(_SCRIV_MD, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(changelog_text, encoding="utf-8")
    (tmp_path / "changelog.d").mkdir()


def test_detect_version_collision_finds_existing_entry(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    assert orchestrate.detect_version_collision("0.65.1") == "0.65.1 — 2026-05-04"


def test_detect_version_collision_returns_none_when_absent(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    assert orchestrate.detect_version_collision("0.65.2") is None


class _RecordingProvider:
    """Provider double that records the calls it received."""

    name = "test"

    def __init__(self, current: str) -> None:
        self._current = current
        self.next_calls: list[str] = []
        self.apply_calls: list[tuple[str, bool, bool, bool]] = []

    def current(self) -> str:
        return self._current

    def next(self, level: str) -> str:
        self.next_calls.append(level)
        return f"next-for-{level}"

    def apply(self, level: str, *, tag: bool, commit: bool, push: bool) -> str:
        self.apply_calls.append((level, tag, commit, push))
        return f"applied-{level}"


_SCRIV_CONFIG_FULL = """\
[tool.scriv]
categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security", "Chore"]
format = "md"
md_header_level = 2
"""


def _setup_with_fragment(tmp_path: Any, fragment: tuple[str, str]) -> None:
    (tmp_path / "pyproject.toml").write_text(_SCRIV_CONFIG_FULL, encoding="utf-8")
    frag_dir = tmp_path / "changelog.d"
    frag_dir.mkdir()
    name, body = fragment
    (frag_dir / name).write_text(body, encoding="utf-8")


def test_compute_next_version_downshifts_in_zero_major(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_with_fragment(tmp_path, ("a.md", "### Removed\n\n- breaking change\n"))
    monkeypatch.chdir(tmp_path)
    provider = _RecordingProvider(current="0.5.0")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.compute_next_version(config=Config(version_provider="test"))

    assert result == ("minor", "next-for-minor")
    assert provider.next_calls == ["minor"]


def test_compute_next_version_strict_preserves_major(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_with_fragment(tmp_path, ("a.md", "### Removed\n\n- breaking change\n"))
    monkeypatch.chdir(tmp_path)
    provider = _RecordingProvider(current="0.5.0")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.compute_next_version(
        config=Config(version_provider="test", zero_major_policy="strict")
    )

    assert result == ("major", "next-for-major")
    assert provider.next_calls == ["major"]


def test_compute_next_version_unaffected_when_major_is_nonzero(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_with_fragment(tmp_path, ("a.md", "### Removed\n\n- breaking change\n"))
    monkeypatch.chdir(tmp_path)
    provider = _RecordingProvider(current="1.2.3")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.compute_next_version(config=Config(version_provider="test"))

    assert result == ("major", "next-for-major")


def test_compute_next_version_returns_none_when_no_fragments(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text(_SCRIV_CONFIG_FULL, encoding="utf-8")
    (tmp_path / "changelog.d").mkdir()
    monkeypatch.chdir(tmp_path)
    provider = _RecordingProvider(current="0.5.0")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    assert (
        orchestrate.compute_next_version(config=Config(version_provider="test")) is None
    )


def _fake_tag_run(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stub subprocess.run to capture git invocations made by _git.finalize."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_tag_release_tags_bumped_version(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tag-based bumping: tag the result of provider.next(level), not current.
    calls = _fake_tag_run(monkeypatch)

    provider = _RecordingProvider(current="1.2.3")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.tag_release(
        level="patch", config=Config(version_provider="test")
    )

    assert result == "next-for-patch"
    assert calls == [["git", "tag", "vnext-for-patch"]]
    assert provider.next_calls == ["patch"]
    assert provider.apply_calls == []  # no file mutation at tag time


def test_tag_release_pushes_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_tag_run(monkeypatch)

    provider = _RecordingProvider(current="1.2.3")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    orchestrate.tag_release(
        level="patch", config=Config(version_provider="test"), push=True
    )

    assert calls == [
        ["git", "tag", "vnext-for-patch"],
        ["git", "push", "--follow-tags"],
    ]


def test_tag_release_applies_zero_major_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `major` on a 0.x project downshifts to `minor` per the default policy,
    # so we tag the minor-bumped version, not the major-bumped one.
    _fake_tag_run(monkeypatch)

    provider = _RecordingProvider(current="0.5.0")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.tag_release(
        level="major", config=Config(version_provider="test")
    )

    assert result == "next-for-minor"
    assert provider.next_calls == ["minor"]


def test_tag_release_strict_passes_major_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_tag_run(monkeypatch)

    provider = _RecordingProvider(current="0.5.0")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.tag_release(
        level="major",
        config=Config(version_provider="test", zero_major_policy="strict"),
    )

    assert result == "next-for-major"
    assert provider.next_calls == ["major"]


def _setup_with_changelog_and_fragment(
    tmp_path: Any, changelog_text: str, fragment: tuple[str, str]
) -> None:
    (tmp_path / "pyproject.toml").write_text(_SCRIV_CONFIG_FULL, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(changelog_text, encoding="utf-8")
    frag_dir = tmp_path / "changelog.d"
    frag_dir.mkdir()
    name, body = fragment
    (frag_dir / name).write_text(body, encoding="utf-8")


def test_latest_changelog_version_returns_highest(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    assert orchestrate.latest_changelog_version() == "0.65.1"


def test_latest_changelog_version_returns_none_when_no_entries(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, "# Changelog\n\n<!-- scriv-insert-here -->\n")
    monkeypatch.chdir(tmp_path)
    assert orchestrate.latest_changelog_version() is None


def test_check_no_orphan_tag_passes_on_match(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.65.1")
    # Should not raise.
    orchestrate.check_no_orphan_tag()


def test_check_no_orphan_tag_skips_when_no_changelog_entries(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Models the "first introduction" case: changelog has no entries yet.
    _setup_scriv_repo(tmp_path, "# Changelog\n\n<!-- scriv-insert-here -->\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.1.0")
    orchestrate.check_no_orphan_tag()


def test_check_no_orphan_tag_skips_when_no_tags(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # First release ever — there are no tags yet, only a CHANGELOG entry that
    # the imminent tag-push will match. Drift check shouldn't fire here.
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: None)
    orchestrate.check_no_orphan_tag()


def test_check_no_orphan_tag_raises_when_tag_is_ahead(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Tag ahead of changelog → orphan/stray tag. Recovery is "delete the
    # stray tag" or "backfill the changelog entry".
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.67.0")
    with pytest.raises(SystemExit) as exc:
        orchestrate.check_no_orphan_tag()
    msg = str(exc.value)
    assert "v0.67.0" in msg
    assert "0.65.1" in msg
    assert "git tag -d v0.67.0" in msg
    assert "git tag -a" not in msg  # the "create tag" hint should NOT show


def test_check_no_orphan_tag_raises_when_tag_is_behind(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Tag behind changelog → previous release added the entry but never
    # tagged. Recovery is "tag the corresponding commit" or "rewind the
    # changelog entry".
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.65.0")
    with pytest.raises(SystemExit) as exc:
        orchestrate.check_no_orphan_tag()
    msg = str(exc.value)
    assert "v0.65.0" in msg
    assert "0.65.1" in msg
    assert "git tag -a v0.65.1" in msg
    assert "git tag -d" not in msg  # the "delete the stray tag" hint should NOT show


def test_compute_next_version_raises_on_orphan_tag(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_with_changelog_and_fragment(
        tmp_path,
        _CHANGELOG_WITH_065,
        ("a.md", "### Fixed\n\n- a fix\n"),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.67.0")
    provider = _RecordingProvider(current="0.65.1")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    with pytest.raises(SystemExit) as exc:
        orchestrate.compute_next_version(config=Config(version_provider="test"))
    assert "v0.67.0" in str(exc.value)
    assert "0.65.1" in str(exc.value)
    assert provider.next_calls == []  # bail before computing next


def test_compute_next_version_passes_when_tag_matches_changelog(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_with_changelog_and_fragment(
        tmp_path,
        _CHANGELOG_WITH_065,
        ("a.md", "### Fixed\n\n- a fix\n"),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.65.1")
    provider = _RecordingProvider(current="0.65.1")
    monkeypatch.setattr(orchestrate, "get_provider", lambda name: provider)

    result = orchestrate.compute_next_version(config=Config(version_provider="test"))
    assert result == ("patch", "next-for-patch")


def test_collect_for_release_raises_on_collision(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_scriv_repo(tmp_path, _CHANGELOG_WITH_065)
    (tmp_path / "changelog.d" / "a.md").write_text(
        "### Fixed\n\n- a fix\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(orchestrate, "latest_git_tag_version", lambda: "0.65.1")

    # Contrived provider whose `next()` returns the latest changelog entry's
    # version — the candidate is already present in CHANGELOG.md, isolating
    # the collision path.
    class FakeProvider:
        name = "test"

        def current(self) -> str:
            return "0.65.1"

        def next(self, level: str) -> str:
            return "0.65.1"

        def apply(self, level: str, *, tag: bool, commit: bool, push: bool) -> str:
            return "0.65.1"

    monkeypatch.setattr(orchestrate, "get_provider", lambda name: FakeProvider())

    config = Config(version_provider="test")
    with pytest.raises(SystemExit) as exc:
        orchestrate.collect_for_release(config=config)
    msg = str(exc.value)
    assert "0.65.1" in msg
    assert "git tag -a v0.65.1" in msg  # collision-specific recovery hint
