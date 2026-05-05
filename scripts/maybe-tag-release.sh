#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

prev_level=$(scriv-release detect-release || true)

if [ -z "${prev_level}" ]; then
  {
    echo "released=false"
  } >> "$GITHUB_OUTPUT"
  echo "No release detected for HEAD; nothing to tag."
  exit 0
fi

git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

scriv-release tag --level "${prev_level}"

new_tag=$(git describe --tags --exact-match HEAD)
git push origin "refs/tags/${new_tag}"

{
  echo "released=true"
  echo "tag=${new_tag}"
} >> "$GITHUB_OUTPUT"
