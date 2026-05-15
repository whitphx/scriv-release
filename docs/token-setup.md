# Token setup

The action needs a token with `contents: write` and `pull-requests: write` permissions to:

- Push the preview branch and any release tag.
- Open and update the changelog preview PR.

There are two options.

## GitHub App (recommended)

When the workflow pushes a tag using the default `GITHUB_TOKEN`, GitHub does **not** trigger downstream workflows (e.g. your "publish to PyPI on tag" workflow). This is by design — to prevent infinite recursion.

To make tag-push trigger downstream workflows, mint the token from a GitHub App that you own. `scriv-release` provides a manifest so you can register the App in one click:

> [!IMPORTANT]
> Creating a GitHub App registers it in your account, but the App can't act on *any* repository until you also **install** it on that repo. These are two separate steps in GitHub's UI. Skipping the install step makes the action fail at runtime with `404 Not Found` when minting a token (`GET /repos/<owner>/<repo>/installation`).

### Quick install (recommended)

1. Open <https://whitphx.github.io/scriv-release/install-app/> and click **Create on your personal account** (or fill the org-name field for an org install).
2. On the GitHub confirmation page, click the green **Create GitHub App** button at the bottom. The App is now registered in your account.
3. You'll be redirected to a callback page that shows the App's private key once. From there:
   - Click **Install** to grant the App access to the repo (or repos) you want `scriv-release` to manage. **This is a separate step from creation** — without it the action's token-minting step gets a 404.
   - Copy the App ID into a repo **variable** `RELEASE_APP_ID`, and the `.pem` into a repo **secret** `RELEASE_APP_KEY`.

### Manual setup

If you'd rather do it by hand:

1. Create a GitHub App in your org or user account at <https://github.com/settings/apps/new>.
   - Repository permissions: `Contents: Read and write`, `Pull requests: Read and write`.
   - Subscribe to events: none required.
2. **Install the App on the repo** (or the whole org). This is a separate step from creation — the App exists in your account once you click *Create GitHub App*, but it can't act on any repository until you also install it. From the App's settings page, click **Install App** in the sidebar and pick the repo (or "All repositories"). Without this step the action fails with `404 Not Found` when trying to mint a token.
3. Generate a private key, copy it.
4. In the repo settings:
   - Add a repository **variable** `RELEASE_APP_ID` set to the App's numeric ID.
   - Add a repository **secret** `RELEASE_APP_KEY` set to the PEM-encoded private key.
5. Reference both in your workflow:

```yaml
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

The action internally uses [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token) to mint a short-lived installation token.

## Default `GITHUB_TOKEN` (limited)

If you don't need tag-push to trigger downstream workflows (e.g. you publish manually, or your publish workflow runs on `release` events triggered some other way), you can skip the App and let the action fall back to `github.token`:

```yaml
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
```

## Using a personal access token (PAT)

Discouraged but possible: pass a fine-grained PAT via `github-token`:

```yaml
- uses: whitphx/scriv-release@v0.3.0
  with:
    github-token: ${{ secrets.MY_PAT }}
```

PATs are tied to a user account; rotate them carefully. App tokens are repo-scoped and short-lived, which is why we recommend them.
