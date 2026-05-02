from __future__ import annotations

import pytest

from scriv_release.versioning._semver import bump_semver


@pytest.mark.parametrize(
    "current,level,expected",
    [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("0.0.0", "patch", "0.0.1"),
        ("1.2.3.dev4", "patch", "1.2.4"),
    ],
)
def test_bump_semver(current: str, level: str, expected: str) -> None:
    assert bump_semver(current, level) == expected  # type: ignore[arg-type]
