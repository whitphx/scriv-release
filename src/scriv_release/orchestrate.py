from __future__ import annotations

import os
import re
import subprocess

from .config import Config, load_config
from .policy import BumpLevel, compute_bump_level
from .versioning import get_provider


def collect_for_release(*, config: Config) -> str | None:
    level = compute_bump_level(config=config)
    if level is None:
        return None
    provider = get_provider(config.version_provider)
    next_version = provider.next(level)
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
    from scriv.util import Version

    target = Version(version)
    if not target:
        return None
    scriv = Scriv()
    changelog = scriv.changelog()
    changelog.read()
    for etitle in changelog.entries().keys():
        if etitle is None:
            continue
        eversion = Version.from_text(etitle)
        if eversion is not None and eversion == target:
            return etitle
    return None


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
    provider = get_provider(config.version_provider)
    return provider.apply(level, tag=True, commit=False, push=push)


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
