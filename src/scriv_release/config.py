from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

UnknownCategoryPolicy = Literal["warn", "error", "patch"]
ReleaseDetection = Literal["history", "pr-body-marker", "auto"]


_DEFAULT_CATEGORY_MAP: dict[str, str] = {
    "Added": "minor",
    "Changed": "minor",
    "Deprecated": "minor",
    "Removed": "major",
    "Fixed": "patch",
    "Security": "patch",
    "Chore": "patch",
}


@dataclass(frozen=True)
class Config:
    category_semver_map: dict[str, str] = field(
        default_factory=lambda: dict(_DEFAULT_CATEGORY_MAP)
    )
    unknown_category_policy: UnknownCategoryPolicy = "warn"
    version_provider: str = "bump-my-version"
    preview_branch: str = "scriv-release-preview"
    release_detection: ReleaseDetection = "history"
    pr_body_marker_key: str = "scriv-release-bump"


def load_config(pyproject_path: Path | None = None) -> Config:
    path = pyproject_path or Path("pyproject.toml")
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("tool", {}).get("scriv-release", {})
    return Config(
        category_semver_map=dict(
            section.get("category_semver_map", _DEFAULT_CATEGORY_MAP)
        ),
        unknown_category_policy=section.get("unknown_category_policy", "warn"),
        version_provider=section.get("version_provider", "bump-my-version"),
        preview_branch=section.get("preview_branch", "scriv-release-preview"),
        release_detection=section.get("release_detection", "history"),
        pr_body_marker_key=section.get("pr_body_marker_key", "scriv-release-bump"),
    )
