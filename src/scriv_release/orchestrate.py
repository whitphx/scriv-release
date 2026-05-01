from __future__ import annotations

import subprocess

from .config import Config
from .policy import BumpLevel, compute_bump_level
from .versioning import get_provider


def collect_for_release(*, config: Config) -> str | None:
    level = compute_bump_level(config=config)
    if level is None:
        return None
    provider = get_provider(config.version_provider)
    next_version = provider.next(level)
    subprocess.run(
        ["scriv", "collect", "--version", next_version],
        check=True,
    )
    return next_version


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
