from __future__ import annotations

import subprocess

from ..policy import BumpLevel
from . import _git
from ._semver import bump_semver


class Provider:
    name = "hatch"

    def current(self) -> str:
        return _run("hatch", "version").strip()

    def next(self, level: BumpLevel) -> str:
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
        _run("hatch", "version", level)
        _git.finalize(new_version, tag=tag, commit=commit, push=push)
        return new_version


def _run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout
