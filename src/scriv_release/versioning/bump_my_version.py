from __future__ import annotations

import subprocess

from ..policy import BumpLevel


class Provider:
    name = "bump-my-version"

    def current(self) -> str:
        return _run("bump-my-version", "show", "current_version").strip()

    def next(self, level: BumpLevel) -> str:
        return _run(
            "bump-my-version", "show", "--increment", level, "new_version"
        ).strip()

    def apply(
        self,
        level: BumpLevel,
        *,
        tag: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> str:
        args = ["bump-my-version", "bump", level, "--verbose"]
        if tag:
            args.append("--tag")
        if not commit:
            args.append("--no-commit")
        _run(*args)
        new_version = self.current()
        if push:
            subprocess.run(["git", "push", "--follow-tags"], check=True)
        return new_version


def _run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout
