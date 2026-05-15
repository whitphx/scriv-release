# Changelog

<!-- scriv-insert-here -->

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
