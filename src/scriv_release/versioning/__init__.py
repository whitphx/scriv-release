from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

from ..policy import BumpLevel


@runtime_checkable
class VersionProvider(Protocol):
    name: str

    def current(self) -> str: ...
    def next(self, level: BumpLevel) -> str: ...
    def apply(
        self,
        level: BumpLevel,
        *,
        tag: bool = True,
        commit: bool = False,
        push: bool = False,
    ) -> str: ...


def get_provider(name: str) -> VersionProvider:
    matches = entry_points(group="scriv_release.version_providers", name=name)
    if not matches:
        raise LookupError(f"No version provider registered as {name!r}")
    cls = next(iter(matches)).load()
    return cls()
