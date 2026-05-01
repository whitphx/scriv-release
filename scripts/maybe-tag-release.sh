#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

# HEAD has no fragments. Inspect HEAD~1: if fragments existed there,
# this commit is the merge of a previously-opened changelog preview PR.
current=$(git rev-parse HEAD)
git checkout --quiet HEAD~1

prev_level=$(scriv-release bump-level || true)

git checkout --quiet "${current}"

if [ -z "${prev_level}" ]; then
  {
    echo "released=false"
  } >> "$GITHUB_OUTPUT"
  echo "No fragments on HEAD~1; nothing to release."
  exit 0
fi

git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

scriv-release tag --level "${prev_level}"

git push origin HEAD --follow-tags

new_tag=$(git describe --tags --exact-match HEAD)

{
  echo "released=true"
  echo "tag=${new_tag}"
} >> "$GITHUB_OUTPUT"
