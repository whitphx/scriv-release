# scriv-release

[![PyPI](https://img.shields.io/pypi/v/scriv-release.svg)](https://pypi.org/project/scriv-release/)
[![Python versions](https://img.shields.io/pypi/pyversions/scriv-release.svg)](https://pypi.org/project/scriv-release/)
[![CI](https://github.com/whitphx/scriv-release/actions/workflows/ci.yml/badge.svg)](https://github.com/whitphx/scriv-release/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/scriv-release.svg)](https://github.com/whitphx/scriv-release/blob/main/LICENSE)

Changesets-style release automation on top of [`scriv`](https://github.com/nedbat/scriv).

`scriv` already manages per-PR changelog fragments. `scriv-release` adds the missing pieces for fully automated releases:

1. A **policy** for mapping changelog categories to semver bump levels.
2. **Orchestration** commands (`bump-level`, `next-version`, `collect`, `tag`) that wrap `scriv` and a configurable version provider.
3. A **GitHub Action** that opens a "Changelog Preview" PR when fragments are pending, and tags a release once that PR is merged — the same flow popularized by [Changesets](https://github.com/changesets/changesets) in the JS ecosystem.

## Quickstart

```bash
pip install "scriv-release[bump-my-version]"
```

```toml
# pyproject.toml
[tool.scriv-release]
version_provider = "bump-my-version"
```

In your repo's `.github/workflows/release.yml`:

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

      - uses: whitphx/scriv-release@v0.4.0
        with:
          client-id: ${{ vars.RELEASE_APP_CLIENT_ID }}
          app-private-key: ${{ secrets.RELEASE_APP_KEY }}
```

`RELEASE_APP_CLIENT_ID` and `RELEASE_APP_KEY` come from a GitHub App that you own. The action mints a short-lived installation token from the App so the tag-push it does at release time can trigger downstream workflows (the default `GITHUB_TOKEN` cannot — by design, to avoid recursion). To skip the manual App-creation flow, open

> **<https://whitphx.github.io/scriv-release/install-app/>**

and click *Create on your personal account* (or fill the org name). GitHub's confirmation page is pre-populated with the recommended permissions (`contents: write`, `pull_requests: write`); submit, and the App is registered under your account. The page then walks you through generating a key, installing the App on the repo, and setting the secrets. See [`docs/token-setup.md`](docs/token-setup.md) for the longer explanation and a manual fallback.

For end-to-end onboarding, see [`docs/quickstart.md`](docs/quickstart.md).

## How it works

Two phases, branched on whether changelog fragments are present on `HEAD`:

- **Fragments present** → `scriv collect` into a `scriv-release-preview` branch and open/update a "Changelog Preview" PR.
- **No fragments on `HEAD`, but fragments on `HEAD~1`** → that means the preview PR was just merged. Determine the bump level from `HEAD~1`'s fragments, tag the release, push the tag.

This is the same file-presence-based detection Changesets uses, so it survives squash, rebase, and merge commits alike.

## Status

Early scaffold. Public API and config keys may shift before `1.0`.

## License

MIT — see [`LICENSE`](LICENSE).
