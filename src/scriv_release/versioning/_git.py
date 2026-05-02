from __future__ import annotations

import subprocess


def finalize(
    new_version: str,
    *,
    tag: bool,
    commit: bool,
    push: bool,
    tag_format: str = "v{version}",
) -> None:
    tag_name = tag_format.format(version=new_version)
    if commit:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Release {tag_name}"],
            check=True,
        )
    if tag:
        subprocess.run(["git", "tag", tag_name], check=True)
    if push:
        subprocess.run(["git", "push", "--follow-tags"], check=True)
