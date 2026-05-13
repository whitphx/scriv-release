from __future__ import annotations

from pathlib import Path

import pytest

from scriv_release.config import Config
from scriv_release.policy import apply_zero_major_policy, compute_bump_level

_SCRIV_CONFIG = """\
[tool.scriv]
categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security", "Chore"]
format = "md"
md_header_level = 2
"""


def _make_repo(
    tmp_path: Path, fragments: list[tuple[str, str]], scriv_config: str = _SCRIV_CONFIG
) -> Path:
    (tmp_path / "pyproject.toml").write_text(scriv_config, encoding="utf-8")
    frag_dir = tmp_path / "changelog.d"
    frag_dir.mkdir()
    for name, body in fragments:
        (frag_dir / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_no_fragments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_repo(tmp_path, [])
    monkeypatch.chdir(tmp_path)
    assert compute_bump_level(config=Config()) is None


def test_added_yields_minor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_repo(tmp_path, [("a.md", "### Added\n\n- new feature\n")])
    monkeypatch.chdir(tmp_path)
    assert compute_bump_level(config=Config()) == "minor"


def test_fixed_only_yields_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_repo(tmp_path, [("a.md", "### Fixed\n\n- bug\n")])
    monkeypatch.chdir(tmp_path)
    assert compute_bump_level(config=Config()) == "patch"


def test_removed_takes_precedence_over_added(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_repo(
        tmp_path,
        [
            ("a.md", "### Added\n\n- new feature\n"),
            ("b.md", "### Removed\n\n- old api\n"),
        ],
    )
    monkeypatch.chdir(tmp_path)
    assert compute_bump_level(config=Config()) == "major"


def test_unknown_category_warns_and_treats_as_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_repo(tmp_path, [("a.md", "### Mystery\n\n- thing\n")])
    monkeypatch.chdir(tmp_path)
    with pytest.warns(UserWarning):
        level = compute_bump_level(config=Config())
    assert level == "patch"


def test_unknown_category_error_policy_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_repo(tmp_path, [("a.md", "### Mystery\n\n- thing\n")])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        compute_bump_level(config=Config(unknown_category_policy="error"))


@pytest.mark.parametrize(
    "level,current,expected",
    [
        ("major", "0.5.0", "minor"),
        ("major", "0.0.0", "minor"),
        ("major", "1.2.3", "major"),
        ("major", "2.0.0", "major"),
        ("minor", "0.5.0", "minor"),
        ("patch", "0.5.0", "patch"),
        ("minor", "1.2.3", "minor"),
    ],
)
def test_zero_major_policy_downshift(
    level: str, current: str, expected: str
) -> None:
    assert (
        apply_zero_major_policy(level, current_version=current, policy="downshift")  # type: ignore[arg-type]
        == expected
    )


@pytest.mark.parametrize(
    "level,current",
    [
        ("major", "0.5.0"),
        ("major", "0.0.0"),
        ("minor", "0.5.0"),
        ("patch", "0.5.0"),
    ],
)
def test_zero_major_policy_strict_is_passthrough(level: str, current: str) -> None:
    assert (
        apply_zero_major_policy(level, current_version=current, policy="strict")  # type: ignore[arg-type]
        == level
    )
