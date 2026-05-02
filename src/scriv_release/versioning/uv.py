from __future__ import annotations

import subprocess

from ..policy import BumpLevel
from . import _git


class Provider:
    name = "uv"

    def current(self) -> str:
        return _run("uv", "version", "--short").strip()

    def next(self, level: BumpLevel) -> str:
        return _run("uv", "version", "--bump", level, "--dry-run", "--short").strip()

    def apply(
        self,
        level: BumpLevel,
        *,
        tag: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> str:
        new_version = _run(
            "uv", "version", "--bump", level, "--short", "--frozen"
        ).strip()
        _git.finalize(new_version, tag=tag, commit=commit, push=push)
        return new_version


def _run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout
