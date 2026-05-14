from __future__ import annotations

from pathlib import Path

from scriv_release.config import Config, load_config


def test_defaults_when_no_pyproject(tmp_path: Path) -> None:
    config = load_config(pyproject_path=tmp_path / "missing.toml")
    assert config == Config()


def test_defaults_when_section_absent(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text("[project]\nname = 'foo'\n", encoding="utf-8")
    config = load_config(pyproject_path=p)
    assert config == Config()


def test_overrides_from_pyproject(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text(
        """
[tool.scriv-release]
version_provider = "hatch"
preview_branch = "release-pr"
release_detection = "pr-body-marker"
unknown_category_policy = "error"
zero_major_policy = "strict"

[tool.scriv-release.category_semver_map]
Added = "minor"
Custom = "major"
""",
        encoding="utf-8",
    )
    config = load_config(pyproject_path=p)
    assert config.version_provider == "hatch"
    assert config.preview_branch == "release-pr"
    assert config.release_detection == "pr-body-marker"
    assert config.unknown_category_policy == "error"
    assert config.zero_major_policy == "strict"
    assert config.category_semver_map == {"Added": "minor", "Custom": "major"}


def test_zero_major_policy_default() -> None:
    assert Config().zero_major_policy == "downshift"
