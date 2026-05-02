from __future__ import annotations

from packaging.version import Version

from ..policy import BumpLevel


def bump_semver(current: str, level: BumpLevel) -> str:
    v = Version(current)
    if level == "major":
        return f"{v.major + 1}.0.0"
    if level == "minor":
        return f"{v.major}.{v.minor + 1}.0"
    return f"{v.major}.{v.minor}.{v.micro + 1}"
