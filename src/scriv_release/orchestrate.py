from __future__ import annotations

import os
import re
import subprocess

from packaging.version import InvalidVersion, Version

from .config import Config, load_config
from .policy import BumpLevel, apply_zero_major_policy, compute_bump_level
from .versioning import _git, get_provider


def compute_next_version(*, config: Config) -> tuple[BumpLevel, str] | None:
    level = compute_bump_level(config=config)
    if level is None:
        return None
    check_no_orphan_tag()
    provider = get_provider(config.version_provider)
    current = provider.current()
    effective = apply_zero_major_policy(
        level,
        current_version=current,
        policy=config.zero_major_policy,
    )
    return effective, provider.next(effective)


def collect_for_release(*, config: Config) -> str | None:
    result = compute_next_version(config=config)
    if result is None:
        return None
    _, next_version = result
    existing = detect_version_collision(next_version)
    if existing is not None:
        raise SystemExit(_collision_message(next_version, existing))
    subprocess.run(
        ["scriv", "collect", "--version", next_version],
        check=True,
    )
    return next_version


def detect_version_collision(version: str) -> str | None:
    """Return the existing changelog entry title if `version` is already present, else None.

    Mirrors scriv's own collision check (see scriv.collect): an entry whose parsed
    Version matches the candidate is treated as a collision. The candidate is also
    parsed via scriv's Version so the comparison is symmetric with what scriv would
    detect itself.
    """
    from scriv.scriv import Scriv
    from scriv.util import Version as ScrivVersion

    target = ScrivVersion(version)
    if not target:
        return None
    scriv = Scriv()
    changelog = scriv.changelog()
    changelog.read()
    for etitle in changelog.entries().keys():
        if etitle is None:
            continue
        eversion = ScrivVersion.from_text(etitle)
        if eversion is not None and eversion == target:
            return etitle
    return None


def latest_changelog_version() -> str | None:
    """Return the highest parseable version in CHANGELOG.md, or None if there are no entries.

    Returns None for a changelog with no entries (e.g. when scriv-release is being
    introduced to a repo for the first time) — callers should treat that as
    "no released version to compare against".
    """
    from scriv.scriv import Scriv
    from scriv.util import Version as ScrivVersion

    scriv = Scriv()
    changelog = scriv.changelog()
    changelog.read()
    versions: list[Version] = []
    for etitle in changelog.entries().keys():
        if etitle is None:
            continue
        eversion = ScrivVersion.from_text(etitle)
        if eversion is None:
            continue
        try:
            versions.append(Version(str(eversion)))
        except InvalidVersion:
            continue
    if not versions:
        return None
    return str(max(versions))


def latest_git_tag_version() -> str | None:
    """Return the highest parseable v* git tag, or None if there are none.

    Used as the source of truth for "what version is currently released",
    independent of any in-tree version-bearing file. The latter can legitimately
    drift from the tagged version for projects whose committed `pyproject.toml`
    `[project].version` is a stale placeholder (e.g. `hatch-vcs`-style dynamic
    versioning, or "stamp at publish" flows). The git tag, by contrast, is the
    authoritative record of what was actually released.
    """
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    versions: list[Version] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name:
            continue
        try:
            versions.append(Version(name.lstrip("v")))
        except InvalidVersion:
            continue
    if not versions:
        return None
    return str(max(versions))


def check_no_orphan_tag() -> None:
    """Raise SystemExit if the latest git tag has no matching CHANGELOG.md entry.

    This catches the case where a previous run pushed a tag without leaving a
    record in CHANGELOG.md (the v0.67.0 mishap), so the next-version
    computation would otherwise roll forward from a version that was never
    actually released.

    No-op when either side is empty (first-time use in a fresh repo).
    """
    latest_tag = latest_git_tag_version()
    latest_changelog = latest_changelog_version()
    if latest_tag is None or latest_changelog is None:
        return
    if Version(latest_tag) == Version(latest_changelog):
        return
    raise SystemExit(
        _drift_message(latest_tag=latest_tag, latest_changelog=latest_changelog)
    )


def _drift_message(*, latest_tag: str, latest_changelog: str) -> str:
    return (
        f"\nThe latest git tag is v{latest_tag} but the most recent "
        f"CHANGELOG.md entry is {latest_changelog!r}.\n"
        f"\n"
        f"This usually means a stale or orphan tag was created — for example,\n"
        f"a leftover from a partially-completed previous release attempt — that\n"
        f"doesn't correspond to any released changelog entry. Continuing would\n"
        f"compute the next version against the stray tag and produce a release\n"
        f"number that doesn't follow the changelog history.\n"
        f"\n"
        f"To recover, either:\n"
        f"  - Delete the stray tag so it stops being read as the latest, e.g.:\n"
        f"        git tag -d v{latest_tag}\n"
        f"        git push origin :refs/tags/v{latest_tag}\n"
        f"  - Or add the missing CHANGELOG.md entry for {latest_tag} if that\n"
        f"    version really was released and the changelog is what's out of date.\n"
        f"\n"
        f"After reconciling, re-run scriv-release.\n"
    )


def _collision_message(version: str, existing: str) -> str:
    return (
        f"\nThe changelog already has an entry for version {version} "
        f"(found {existing!r}).\n"
        f"\n"
        f"This usually means a previous release attempt updated the changelog\n"
        f"but never pushed the v{version} tag — leaving the project in an\n"
        f"inconsistent state. The version provider sees an older tag as current\n"
        f"and recomputes the same next-version on every subsequent run.\n"
        f"\n"
        f"To recover, find the commit that introduced the {existing!r} entry\n"
        f'(typically the merge of the previous "Changelog Preview" PR) and tag it:\n'
        f"\n"
        f"  git tag -a v{version} <commit> -m 'Release {version}'\n"
        f"  git push origin v{version}\n"
        f"\n"
        f"After that, the next scriv-release run will compute the next-version\n"
        f"correctly.\n"
    )


def print_changelog(*, version: str) -> str:
    result = subprocess.run(
        ["scriv", "print", "--version", version],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def tag_release(*, level: BumpLevel, config: Config, push: bool = False) -> str:
    # Tag-based bumping: compute the new version by bumping the provider's
    # current() by `level`, then push that as the release tag. No file
    # mutations. Works directly for tag-only providers (bump-my-version with
    # no `[tool.bumpversion]`, hatch-vcs) where `current()` is the latest
    # tag; works for file-based providers too, but the committed file may
    # drift behind the tag — projects that need the file in sync should
    # switch to a dynamic-version setup (hatch-vcs, setuptools-scm, etc.).
    provider = get_provider(config.version_provider)
    effective = apply_zero_major_policy(
        level,
        current_version=provider.current(),
        policy=config.zero_major_policy,
    )
    new_version = provider.next(effective)
    _git.finalize(new_version, tag=True, commit=False, push=push)
    return new_version


def parse_marker(body: str, *, key: str) -> BumpLevel | None:
    pattern = re.compile(
        rf"^[ \t]*{re.escape(key)}[ \t]*:[ \t]*(major|minor|patch)[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(body)
    if match is None:
        return None
    return match.group(1).lower()  # type: ignore[return-value]


def detect_release(*, config: Config) -> BumpLevel | None:
    mode = config.release_detection
    if mode in ("pr-body-marker", "auto"):
        body = _fetch_head_pr_body()
        if body is not None:
            level = parse_marker(body, key=config.pr_body_marker_key)
            if level is not None:
                return level
        if mode == "pr-body-marker":
            return None
    return _detect_via_fragment_history()


def _fetch_head_pr_body() -> str | None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return None
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result = subprocess.run(
        [
            "gh",
            "api",
            f"/repos/{repo}/commits/{head}/pulls",
            "--jq",
            ".[0].body // empty",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    body = result.stdout.strip()
    return body or None


def _detect_via_fragment_history() -> BumpLevel | None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "--quiet", "HEAD~1"], check=True)
    try:
        return compute_bump_level(config=load_config())
    finally:
        subprocess.run(["git", "checkout", "--quiet", head], check=True)
