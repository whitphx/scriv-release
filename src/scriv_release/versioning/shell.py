from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ..policy import BumpLevel
from . import _git
from ._semver import bump_semver


class Provider:
    name = "shell"

    def __init__(self) -> None:
        self._cmds = _load_commands()

    def current(self) -> str:
        return _run(self._require("current")).strip()

    def next(self, level: BumpLevel) -> str:
        cmd = self._cmds.get("next")
        if cmd:
            return _run(cmd, env={"LEVEL": level}).strip()
        return bump_semver(self.current(), level)

    def apply(
        self,
        level: BumpLevel,
        *,
        tag: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> str:
        new_version = self.next(level)
        _run(
            self._require("apply"),
            env={"LEVEL": level, "NEW_VERSION": new_version},
        )
        _git.finalize(new_version, tag=tag, commit=commit, push=push)
        return new_version

    def _require(self, key: str) -> str:
        cmd = self._cmds.get(key)
        if not cmd:
            raise RuntimeError(
                f"shell provider requires [tool.scriv-release.shell].{key} "
                "in pyproject.toml"
            )
        return cmd


def _load_commands(pyproject_path: Path | None = None) -> dict[str, str]:
    path = pyproject_path or Path("pyproject.toml")
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("tool", {}).get("scriv-release", {}).get("shell", {})
    return {k: str(v) for k, v in section.items()}


def _run(command: str, *, env: dict[str, str] | None = None) -> str:
    merged = {**os.environ, **(env or {})}
    result = subprocess.run(
        command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
        env=merged,
    )
    return result.stdout
