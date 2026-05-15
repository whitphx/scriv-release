# Changelog

<!-- scriv-insert-here -->

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
