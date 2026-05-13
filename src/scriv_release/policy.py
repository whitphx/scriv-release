from __future__ import annotations

import warnings
from typing import Literal

from packaging.version import Version
from scriv.scriv import Scriv

from .config import Config, ZeroMajorPolicy

BumpLevel = Literal["major", "minor", "patch"]

_PRECEDENCE: tuple[BumpLevel, ...] = ("major", "minor", "patch")


def compute_bump_level(*, config: Config) -> BumpLevel | None:
    scriv = Scriv()
    fragments = scriv.fragments_to_combine()
    if not fragments:
        return None

    entries = scriv.combine_fragments(fragments)
    levels: set[BumpLevel] = set()
    for category in entries.keys():
        mapped = (
            config.category_semver_map.get(category) if category is not None else None
        )
        if mapped is not None:
            levels.add(mapped)  # type: ignore[arg-type]
            continue
        if config.unknown_category_policy == "error":
            raise ValueError(f"Unknown changelog category: {category!r}")
        if config.unknown_category_policy == "warn":
            warnings.warn(
                f"Unknown changelog category {category!r}; treating as 'patch'.",
                stacklevel=2,
            )
        levels.add("patch")

    for level in _PRECEDENCE:
        if level in levels:
            return level
    return None


def apply_zero_major_policy(
    level: BumpLevel, *, current_version: str, policy: ZeroMajorPolicy
) -> BumpLevel:
    # SemVer §4: 0.x.y is unstable; a "major" bump stays inside 0.x rather
    # than graduating to 1.0.0. "strict" opts out — e.g. when the maintainer
    # is ready to graduate.
    if policy == "strict":
        return level
    if level != "major":
        return level
    if Version(current_version).major != 0:
        return level
    return "minor"
