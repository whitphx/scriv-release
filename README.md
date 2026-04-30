# scriv-release

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

jobs:
  release:
    uses: whitphx/scriv-release/.github/workflows/reusable.yml@v1
    secrets:
      app-id: ${{ vars.RELEASE_APP_ID }}
      app-private-key: ${{ secrets.RELEASE_APP_KEY }}
```

See [`docs/quickstart.md`](docs/quickstart.md) and [`docs/token-setup.md`](docs/token-setup.md).

## How it works

Two phases, branched on whether changelog fragments are present on `HEAD`:

- **Fragments present** → `scriv collect` into a `scriv-release-preview` branch and open/update a "Changelog Preview" PR.
- **No fragments on `HEAD`, but fragments on `HEAD~1`** → that means the preview PR was just merged. Determine the bump level from `HEAD~1`'s fragments, tag the release, push the tag.

This is the same file-presence-based detection Changesets uses, so it survives squash, rebase, and merge commits alike.

## Status

Early scaffold. Public API and config keys may shift before `1.0`.

## License

MIT — see [`LICENSE`](LICENSE).
