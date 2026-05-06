# The changesets pattern

`scriv-release` implements the workflow popularized by [Changesets](https://github.com/changesets/changesets) in the JavaScript ecosystem. If you haven't run into Changesets before — or if you have but never thought about *why* it's shaped the way it is — this page explains the pattern from first principles. The implementation in `scriv-release` is then mostly a direct translation onto Python tooling ([`scriv`](https://github.com/nedbat/scriv) for changelog fragments, plus a pluggable version-bumper).

## The problem

A "release" is more than just `git tag v1.4.0`. To ship a maintained library you have to keep three things in sync:

1. The **version** in your source / metadata (e.g. `pyproject.toml`).
2. The **changelog** — what changed since the previous release.
3. A **tag** that marks the commit users should depend on.

If you do these by hand on a release day, you have to read every PR since the last tag, classify the change (was that a fix? a breaking change? a tiny doc fix?), aggregate the human-readable summary, decide the SemVer bump, edit `CHANGELOG.md`, edit the version, commit, tag, push. It works for one maintainer; it scales badly. The classifications often have to be reconstructed from commit messages, which forces you into one of the popular workarounds.

## What conventional approaches give up

Most release-automation tools converge on one of three tradeoffs:

**Manual changelog, merge-day pain.** The changelog is a regular file. Every PR that touches `CHANGELOG.md` near the top conflicts with every other PR that touches it. The release manager spends merge day resolving conflicts.

**Commit-message scraping** (Conventional Commits + tools like `release-please`, `semantic-release`). The commit message *is* the source of truth: you write `feat: …`, `fix: …`, `feat!: …`, and an automation parses messages to build the changelog and decide the bump. This works, but it's brittle: squash commits collapse multiple intents into one message, rebases rewrite messages, merge commits introduce subjects the author never wrote, and the message format becomes a thing reviewers have to police. It also couples the *changelog narrative* (a UX concern) to commit *style* (a developer-history concern), which often pulls in opposite directions.

**Hand-tagged "release commits"** (a maintainer prepares a PR that bumps the version and edits the changelog manually, then tags after merge). This is what most pre-Changesets JS projects did. It's labor-intensive and a single maintainer becomes a serialization point.

## The changesets idea

Changesets sidesteps the merge-conflict and commit-message-scraping problems by recording each change in a **separate file** that lives next to the change itself.

- When you author a PR, you include a small markdown file (a "fragment" or "changeset") in a known directory — `.changeset/` in JS, `changelog.d/` in `scriv` — saying *"this PR adds a feature"* or *"fixes a bug"* together with the human-readable note. The fragment also carries the SemVer category (Added / Fixed / Removed / …).
- Every PR adds a *new* file. Two PRs touching the changelog don't conflict because they're touching different files.
- The changelog itself stays out of `main` until release time. Reviewers don't have to police commit-message style; the fragment is reviewed as part of the PR like any other code.

Then a separate **release loop** consumes the accumulated fragments:

1. When fragments are present on `main`, a bot opens (or updates) a single **"Changelog Preview" PR**. This PR collapses every accumulated fragment into a real `CHANGELOG.md` edit, picks the next version from the highest-precedence category in the bunch (a `Removed` makes it major, a `Fixed` is patch, etc.), bumps the version, and removes the now-consumed fragment files.
2. When you're ready to release, you merge that PR. The bot sees that `main` no longer has fragments (but `main~1` did) and concludes the merge *was* the release. It pushes a tag at the merged commit.

That second step — using **file presence** to detect "this is a release" — is the part that quietly does the most work. It survives squash, rebase, octopus merge, and merge-commit cleanup, because the question being asked isn't "what does the commit message say?" but "did fragments exist before this commit and do they not exist now?"

## Why this is nicer than the alternatives

- **Fragments encode *intent*, not history.** The author says "this PR adds a feature" once, when the change is fresh, in a markdown file that the human will read in the changelog. Reviewers see the user-visible note inline with the diff. No commit-message format to memorize.
- **No merge conflicts on the changelog.** Each PR drops its own file. The conflict surface for parallel PRs is empty.
- **The release is a PR.** Maintainers (and reviewers, and CI) see the proposed changelog and version bump *before* tagging. If something looks wrong, you push a fix to the preview branch and the bot updates the PR. Tagging is the act of merging — no separate "publish" command, no out-of-band coordination.
- **Detection is robust under merge styles.** Squash, rebase, merge-commit — all collapse the same fragments differently in commit history but identically in working-tree state. The release-detection logic works on working-tree state, so all merge styles are equivalent.
- **Decoupled from version semantics.** Whatever your "version" comes from — a static `pyproject.toml` field, `bump-my-version`, `hatch-vcs`, a shell command — the fragment-based decision of *what bump to apply* is independent. `scriv-release` plugs different version providers into the same pattern.

## How `scriv-release` realizes this

The mapping is direct:

| Changesets concept                       | `scriv-release` implementation                                          |
| ---------------------------------------- | ----------------------------------------------------------------------- |
| Per-PR fragment file                     | `changelog.d/<timestamp>_<author>_<topic>.md`, created via `scriv create`. |
| Fragment categories → SemVer bump        | `[tool.scriv-release.category_semver_map]` in `pyproject.toml`.         |
| Bot that opens the preview PR            | The `scriv-release` GitHub Action's "open or update preview PR" path.   |
| Preview PR collapses fragments + bumps   | `scriv collect` + the configured version provider (`bump-my-version`, `hatch`, `uv`, or `shell`). |
| Release detection (file-presence)        | `scriv-release detect-release`: `main` has no fragments, `main~1` did.  |
| Tag push                                 | The action's "tag release" path (run after the preview PR is merged).   |

The author flow is: each PR runs `scriv create`, the author edits the generated fragment to add a one-line description under the right category, commits it. That's it. Everything else is the action.

If you've used Changesets before, the "Pull Request" the JS bot opens corresponds to the "Changelog Preview" PR; the merge-the-PR-to-release semantics are the same.

## Read more

- [Changesets — original JS implementation and design notes](https://github.com/changesets/changesets)
- [`scriv` — the changelog-fragment tool `scriv-release` builds on](https://github.com/nedbat/scriv)
- [Quickstart](quickstart.md) — concrete setup for a Python project.
