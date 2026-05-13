from __future__ import annotations

import argparse
import sys

from .config import load_config
from .orchestrate import (
    collect_for_release,
    compute_next_version,
    detect_release,
    print_changelog,
    tag_release,
)
from .policy import compute_bump_level


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scriv-release")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("bump-level", help="Print the bump level (major|minor|patch).")
    sub.add_parser("next-version", help="Print the next version string.")
    sub.add_parser(
        "detect-release",
        help=(
            "Print the bump level for an in-progress release based on "
            "the configured detection mode, or empty if none."
        ),
    )

    sub.add_parser("collect", help="Run scriv collect with the auto-computed version.")

    p_print = sub.add_parser("print", help="Print the changelog for a version.")
    g = p_print.add_mutually_exclusive_group(required=True)
    g.add_argument("--next", action="store_true", dest="use_next")
    g.add_argument("--version", default=None)

    p_tag = sub.add_parser("tag", help="Bump and tag a release.")
    p_tag.add_argument("--push", action="store_true")
    p_tag.add_argument(
        "--level",
        choices=["major", "minor", "patch"],
        default=None,
        help="Override the level instead of inferring from current fragments.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.cmd == "bump-level":
        level = compute_bump_level(config=config)
        if level:
            print(level)
        return 0

    if args.cmd == "detect-release":
        level = detect_release(config=config)
        if level:
            print(level)
        return 0

    if args.cmd == "next-version":
        result = compute_next_version(config=config)
        if result is None:
            print("No version bump needed.", file=sys.stderr)
            return 0
        print(result[1])
        return 0

    if args.cmd == "collect":
        next_version = collect_for_release(config=config)
        if next_version is None:
            print("No fragments to collect.", file=sys.stderr)
            return 0
        print(next_version)
        return 0

    if args.cmd == "print":
        if args.use_next:
            result = compute_next_version(config=config)
            if result is None:
                return 0
            version = result[1]
        else:
            version = args.version
        sys.stdout.write(print_changelog(version=version))
        return 0

    if args.cmd == "tag":
        level = args.level or compute_bump_level(config=config)
        if level is None:
            print("No version bump needed.", file=sys.stderr)
            return 0
        tag_release(level=level, config=config, push=args.push)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
