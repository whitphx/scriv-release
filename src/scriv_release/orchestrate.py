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
    provider = get_provider(config.version_provider)
    current = provider.current()
    check_provider_in_sync_with_changelog(current_version=current)
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
    level, next_version = result
    existing = detect_version_collision(next_version)
    if existing is not None:
        raise SystemExit(_collision_message(next_version, existing))
    subprocess.run(
        ["scriv", "collect", "--version", next_version],
        check=True,
    )
    # Bump the version-file(s) (pyproject.toml etc.) in the working tree as part
    # of the same preview commit. This keeps the released state in a single
    # commit — the preview-PR merge commit — so the tag in tag_release just
    # points at HEAD without needing a separate "Release vX.Y.Z" commit.
    provider = get_provider(config.version_provider)
    provider.apply(level, tag=False, commit=False, push=False)
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


def check_provider_in_sync_with_changelog(*, current_version: str) -> None:
    """Raise SystemExit if the version provider's current disagrees with CHANGELOG.md.

    No-op when CHANGELOG.md has no version entries yet — that's the expected state
    when scriv-release is first introduced to a repo, and there's nothing to
    compare against.
    """
    latest = latest_changelog_version()
    if latest is None:
        return
    try:
        if Version(current_version) == Version(latest):
            return
    except InvalidVersion:
        # An unparseable provider version is its own problem; let downstream
        # callers surface the failure rather than masking it here.
        return
    raise SystemExit(_drift_message(current=current_version, latest=latest))


def _drift_message(*, current: str, latest: str) -> str:
    return (
        f"\nThe version provider reports the current version as {current!r}, "
        f"but the most recent CHANGELOG.md entry is {latest!r}.\n"
        f"\n"
        f"This usually means a stale or orphan tag is present — for example,\n"
        f"a leftover from a partially-completed previous release attempt — so\n"
        f"the provider reads a version that was never actually released.\n"
        f"Continuing would compute the next version against the stray tag and\n"
        f"produce a release number that doesn't follow the changelog history.\n"
        f"\n"
        f"To recover, either:\n"
        f"  - Delete the stray tag so the provider returns to the released\n"
        f"    version, e.g.:\n"
        f"        git tag -d v{current}\n"
        f"        git push origin :refs/tags/v{current}\n"
        f"  - Or add the missing CHANGELOG.md entry for {current} if that\n"
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
    # By the time we tag, the preview-PR flow has already bumped the version
    # file(s) and merged that commit to main, so `provider.current()` reflects
    # the pending release. We just tag HEAD with that version — no second bump,
    # no extra commit. `level` is kept in the signature so the action's
    # "is this a release commit?" gate (which passes the detected level
    # through) stays unchanged.
    del level
    provider = get_provider(config.version_provider)
    version = provider.current()
    _git.finalize(version, tag=True, commit=False, push=push)
    return version


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
