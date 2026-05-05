---
hide:
  - navigation
  - toc
---

# Ship releases without leaving the PR

`scriv-release` opens a "Changelog Preview" PR when fragments are pending, then tags a release the moment that PR is merged. It's the [Changesets][changesets] workflow, brought to Python on top of [`scriv`][scriv].

[changesets]: https://github.com/changesets/changesets
[scriv]: https://github.com/nedbat/scriv

[:material-rocket-launch: Install the GitHub App](install-app/){ .md-button .md-button--primary }
[:material-book-open-variant: Read the quickstart](quickstart.md){ .md-button }

---

## How it works

<div class="grid cards" markdown>

-   :material-file-edit-outline:{ .lg .middle } **1. Author drops a fragment**

    ---

    Each PR runs `scriv create` and ships a small markdown file under `changelog.d/` categorizing the change.

-   :material-source-pull:{ .lg .middle } **2. Action opens a preview PR**

    ---

    When fragments land on `main`, `scriv-release` collects them, computes the next version from the categories, and opens (or updates) a single "Changelog Preview" PR.

-   :material-tag-outline:{ .lg .middle } **3. Merging the preview tags the release**

    ---

    Merging the preview removes the fragments. The next run sees that, infers the bump level from `HEAD~1`, and pushes the tag.

</div>

---

## Why scriv-release

<div class="grid cards" markdown>

-   :material-source-merge:{ .lg .middle } **Survives squash, rebase, and merge**

    ---

    Detection is file-presence based — not commit-message scraping — so any merge style works and history rewrites don't break it.

-   :material-puzzle-outline:{ .lg .middle } **Bring your own version source**

    ---

    Pluggable providers for `bump-my-version`, `hatch`, `uv`, or a custom shell command. Register your own via entry points.

-   :material-shield-check-outline:{ .lg .middle } **Doesn't fight your toolchain**

    ---

    Installs into a private venv under `$RUNNER_TEMP`. No `setup-python`, no site-packages pollution, no clash with jobs that already have a Python set up.

</div>

---

## Drop-in workflow

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

Then [register the GitHub App](install-app/) for the `RELEASE_APP_ID` / `RELEASE_APP_KEY` secrets and you're done. See [Quickstart](quickstart.md) for the full setup, and [Token setup](token-setup.md) for the App rationale and manual fallback.
