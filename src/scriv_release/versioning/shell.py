from __future__ import annotations

from ..policy import BumpLevel


class Provider:
    name = "shell"

    def current(self) -> str:
        raise NotImplementedError("shell provider not implemented yet")

    def next(self, level: BumpLevel) -> str:
        raise NotImplementedError("shell provider not implemented yet")

    def apply(
        self,
        level: BumpLevel,
        *,
        tag: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> str:
        raise NotImplementedError("shell provider not implemented yet")
