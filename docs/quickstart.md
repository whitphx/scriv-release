# Quickstart

This guide walks through setting up `scriv-release` in a Python project that already has, or wants to add, [`scriv`](https://github.com/nedbat/scriv)-managed changelog fragments.

## 1. Install

```bash
pip install "scriv-release[bump-my-version]"
```

The `[bump-my-version]` extra installs the default version provider. Other providers (`hatch`, `uv`, `shell`) are exposed via entry points — see "Version providers" below.

## 2. Configure scriv

If you don't already have a scriv config, add this to `pyproject.toml`:

```toml
[tool.scriv]
categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security", "Chore"]
format = "md"
md_header_level = 2
```

## 3. Configure scriv-release

Add the `[tool.scriv-release]` section. All keys are optional — defaults match the table below.

```toml
[tool.scriv-release]
version_provider = "bump-my-version"
preview_branch = "scriv-release-preview"
unknown_category_policy = "warn"   # "warn" | "error" | "patch"
release_detection = "history"      # "history" | "pr-body-marker" | "auto"
zero_major_policy = "downshift"    # "downshift" | "strict"

[tool.scriv-release.category_semver_map]
Added = "minor"
Changed = "minor"
Deprecated = "minor"
Removed = "major"
Fixed = "patch"
Security = "patch"
Chore = "patch"
```

### `zero_major_policy`

Per [SemVer §4](https://semver.org/#spec-item-4), `0.x.y` releases have no stable public API and may break at any minor bump. `zero_major_policy` controls how this interacts with `category_semver_map` while the current version's major is `0`:

| Mode         | Behavior while `major == 0`                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| `downshift`  | Default. A `"major"`-level fragment (e.g. `Removed`) bumps the **minor** position. `0.5.0` → `0.6.0`.    |
| `strict`     | Apply bumps positionally regardless. `0.5.0` + `Removed` → `1.0.0`.                                      |

When you're ready to graduate to `1.0.0`, set `zero_major_policy = "strict"` (or manually set the version to `1.0.0` in your version-bearing file before the next release). Once the major is `1` or higher this setting is a no-op.

## 4. Configure bump-my-version

`scriv-release` delegates the actual version bump to your chosen version provider. For `bump-my-version`, see [its docs](https://callowayproject.github.io/bump-my-version/) — the minimum is a `[tool.bumpversion]` section in `pyproject.toml` pointing at your version string.

## 5. Wire up the GitHub Action

Add `.github/workflows/release.yml`:

```yaml
on:
  push:
    branches: [main]

permissions: {}

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
          persist-credentials: false

      - uses: whitphx/scriv-release@v0.3.0
        with:
          app-id: ${{ vars.RELEASE_APP_ID }}
          app-private-key: ${{ secrets.RELEASE_APP_KEY }}
```

The action installs `scriv-release` into a private venv under `$RUNNER_TEMP` — it does not run `setup-python` or pollute the caller's site-packages, so it can sit alongside a job that already has its own Python toolchain. By default the install source is the action's own pinned checkout (`$GITHUB_ACTION_PATH[bump-my-version]`), so the workflow ref is the only place a version is named: `@v0.3.0` always installs the v0.3.0 source. To use a different extra or a published wheel, pass `install-spec` (any pip-style requirement):

```yaml
      - uses: whitphx/scriv-release@v0.3.0
        with:
          install-spec: scriv-release[hatch]==0.3.0
```

See [`token-setup.md`](token-setup.md) for the GitHub App and why the default `GITHUB_TOKEN` isn't enough.

## 6. Author flow

For each PR, contributors run:

```bash
scriv create --edit
```

This opens an editor on a new file in `changelog.d/`. Fill in the relevant section(s) (`### Added`, `### Fixed`, …) and commit it with the PR.

When the PR is merged to `main`, the action opens (or updates) a "Changelog Preview for Next Release" PR. Merging that PR triggers a tagged release.

## CLI cheatsheet

```bash
scriv-release bump-level     # major | minor | patch | (empty)
scriv-release next-version   # e.g. 1.4.0
scriv-release detect-release # bump level for an in-progress release, per release_detection
scriv-release collect        # runs `scriv collect --version <next>`
scriv-release print --next   # changelog body for the next version
scriv-release tag --push     # bump + tag + push (local release)
```

## Version providers

Configured via `[tool.scriv-release].version_provider`. Built-ins:

| Name              | Notes                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------- |
| `bump-my-version` | Default. Requires the `[bump-my-version]` extra. Tagging/commit handled by bump-my-version's own config. |
| `hatch`           | Uses `hatch version`. Requires `[tool.hatch.version]` to be configured (dynamic source). Tag is `v{version}`. |
| `uv`              | Uses `uv version`. Tag is `v{version}`.                                                |
| `shell`           | Runs user-supplied commands. See below.                                                |

Third parties can register additional providers via the `scriv_release.version_providers` entry-point group.

### Shell provider

Configure the commands under `[tool.scriv-release.shell]`:

```toml
[tool.scriv-release]
version_provider = "shell"

[tool.scriv-release.shell]
current = "cat VERSION"
apply = "./scripts/bump.sh"   # receives $LEVEL and $NEW_VERSION; writes the new version into source
# next = "..."                # optional; defaults to packaging-based major/minor/patch bump of `current`
```

The `apply` command must update version-bearing files; `scriv-release` then handles `git tag`/`git push`.

## Release detection

`release_detection` controls how the action knows that the current `main` HEAD is the merged preview PR (i.e. the moment to tag a release).

| Mode             | Behavior                                                                                                                                       |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `history`        | Default. If HEAD has no fragments and HEAD~1 did, treat as release. Survives squash/rebase/merge.                                              |
| `pr-body-marker` | Look up the PR for HEAD via `gh api`, parse a marker like `scriv-release-bump: minor` from the body, and use it as the bump level.             |
| `auto`           | Try `pr-body-marker` first; fall back to `history` if no marker is present.                                                                    |

The marker key defaults to `scriv-release-bump` and can be customized:

```toml
[tool.scriv-release]
release_detection = "pr-body-marker"
pr_body_marker_key = "release-kind"   # then PR body would contain `release-kind: minor`
```
