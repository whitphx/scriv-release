# Changelog

<!-- scriv-insert-here -->

<a id='changelog-0.6.0'></a>
## 0.6.0 — 2026-05-16

### Changed

- Switch to tag-based bumping at release time. `tag_release` now tags `provider.next(level)` (the bump of the current version), so it works for tag-only providers — `bump-my-version` with no `[tool.bumpversion]` config, `hatch-vcs`-style projects — where the preview PR has no file to bump and `provider.current()` still reports the previous tag at merge time. This unblocks streamlit-webrtc's release flow, which Option A (v0.5.0–v0.5.1) had crashed with `fatal: tag 'vX.Y.Z' already exists`. The preview-PR step no longer runs the version-provider's `apply()`; the preview commit carries only the new CHANGELOG entry, and the tag itself is the release. File-based projects that want their committed `[project].version` to track the tag should move to a dynamic-version setup (`hatch-vcs`, `setuptools-scm`, …) or bump the file explicitly in a separate flow.

### Fixed

- Refactor the consistency guard to compare the latest git tag against the most recent CHANGELOG.md entry, rather than comparing the version provider's `current()`. This is provider-independent: it correctly catches orphan or stale tags for tag-based projects, and it doesn't false-positive on file-based projects whose committed version field intentionally lags the tag (e.g. "stamp at publish" workflows).

<a id='changelog-0.5.1'></a>
## 0.5.1 — 2026-05-15

### Fixed

- Pass `--allow-dirty` to `bump-my-version bump` in the `bump-my-version` provider's `apply()` so it tolerates the working-tree state left by `scriv collect` (modified `CHANGELOG.md`, consumed fragment file deleted). Without the flag, `bump-my-version` aborted with `Git working directory is not clean` and the action's "open preview PR" step crashed on every repo using the default provider — a regression introduced in v0.5.0 by moving the version-file bump into the preview-PR step.

<a id='changelog-0.5.0'></a>
## 0.5.0 — 2026-05-15

### Changed

- The Changelog Preview PR now includes the version-file bump (e.g. `[project].version` in `pyproject.toml`) alongside the new `CHANGELOG.md` entry, so merging the preview PR brings everything the release needs into `main` in a single commit. The subsequent tag step just tags that merge commit — no separate "Release vX.Y.Z" commit, and no risk of the tag landing on a commit whose version-bearing files still read the previous release. Previously the provider's `apply()` ran at tag time with `commit=False`, which left the bump in the working tree of the action runner only and let it get discarded; with a file-based provider (`uv`, `bump-my-version` with `[tool.bumpversion]`, `hatch`, or `shell`) that produced silent drift between the tagged commit and the tagged version. Tag-only setups (e.g. `bump-my-version` with no `[tool.bumpversion]` configuration, or `hatch-vcs`-style version-from-tag) keep working unchanged because their `apply()` simply makes no file changes to bundle.

<a id='changelog-0.4.1'></a>
## 0.4.1 — 2026-05-15

### Fixed

- Abort with a clear error before opening a Changelog Preview PR when the version provider's reported current version disagrees with the most recent CHANGELOG.md entry. Previously a stale or orphan tag (e.g. a leftover from a partially-completed previous release attempt) would silently cause the next-version computation to roll forward from a version that was never actually released. The check is skipped when CHANGELOG.md has no entries yet, so first-time introduction of scriv-release to a new repo still works.

<a id='changelog-0.4.0'></a>
## 0.4.0 — 2026-05-15

### Added

- Action input `client-id` for passing the GitHub App's Client ID to the token-minting step.

### Changed

- The default `zero_major_policy` now keeps a `"major"`-level fragment (e.g. `Removed`) inside `0.x` instead of graduating to `1.0.0` — per [SemVer §4](https://semver.org/#spec-item-4), the public API of a `0.x.y` project is unstable. Set `zero_major_policy = "strict"` in `[tool.scriv-release]` to opt back into positional bumping when graduating to `1.0.0`.

### Removed

- Action input `app-id` (deprecated upstream by [`actions/create-github-app-token@v3.2.0`](https://github.com/actions/create-github-app-token/releases/tag/v3.2.0)). Pass the App's Client ID via the new `client-id` input instead. The repo-side convention shifts from variable `RELEASE_APP_ID` to `RELEASE_APP_CLIENT_ID`; the value to put in it is the App's **Client ID** (alphanumeric, on the App settings page just below the numeric App ID), not the App ID.
