---
hide:
  - navigation
  - toc
---

# Ship releases without leaving the PR

`scriv-release` opens a "Changelog Preview" PR when fragments are pending, then tags a release the moment that PR is merged. It's the [Changesets][changesets] workflow, brought to Python on top of [`scriv`][scriv]. New to that pattern? Read [The changesets pattern](changesets.md) for the *why*.

[changesets]: changesets.md
[scriv]: https://github.com/nedbat/scriv

[:material-book-open-variant: Read the quickstart](quickstart.md){ .md-button .md-button--primary }
[:material-github: View on GitHub](https://github.com/whitphx/scriv-release){ .md-button }

---

## The problem

Shipping a release keeps three things in sync — the **version** in your source, the **changelog**, and the **tag** — across many PRs from many authors. The conventional approaches force a tradeoff:

- Edit `CHANGELOG.md` directly → every PR conflicts at the top of the file.
- Parse commit messages (Conventional Commits, `semantic-release`, …) → squash and rebase mangle the format, merge commits introduce subjects nobody wrote, and reviewers end up policing prose instead of code.

`scriv-release` records each change as its own file in `changelog.d/` (no conflicts) and decides releases from working-tree state (survives any merge style). The longer story — and why this is nicer than the alternatives — is in [The changesets pattern](changesets.md).

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

      - uses: whitphx/scriv-release@v0.4.0
        with:
          client-id: ${{ vars.RELEASE_APP_CLIENT_ID }}
          app-private-key: ${{ secrets.RELEASE_APP_KEY }}
```

The full walkthrough — `scriv` config, category-to-semver mapping, version-provider choice, author flow — lives in the [Quickstart](quickstart.md).

---

## Set up the GitHub App

The action references a variable `RELEASE_APP_CLIENT_ID` and a secret `RELEASE_APP_KEY` that come from a GitHub App you own. The App mints a short-lived installation token so the tag-push the action does at release time can trigger your downstream workflows — the default `GITHUB_TOKEN` deliberately can't, to avoid recursion.

`scriv-release` ships a manifest so you can register a pre-configured App in one click:

[:material-rocket-launch: Install the GitHub App](install-app/){ .md-button .md-button--primary }

The page walks you through generating the key, installing the App on the repo, and wiring the secrets. See [Token setup](token-setup.md) for the manual fallback and the rationale.
