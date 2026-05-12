#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${DEFAULT_BRANCH:?DEFAULT_BRANCH is required}"
: "${PREVIEW_BRANCH:?PREVIEW_BRANCH is required}"
: "${NEXT_VERSION:?NEXT_VERSION is required}"

scriv-release collect

git add -A
git commit -m "Preview changelog for next release (${NEXT_VERSION})"

git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
git push origin "HEAD:${PREVIEW_BRANCH}" --force

changelog_content=$(scriv-release print --version "${NEXT_VERSION}")
preview_body=$(printf "# Changelog Preview for Version %s\n\n%s\n" "${NEXT_VERSION}" "${changelog_content}")

existing_pr=$(gh pr list --head "${PREVIEW_BRANCH}" --json number --jq '.[0].number')
if [ -n "${existing_pr}" ]; then
  gh pr edit "${existing_pr}" \
    --title "Changelog Preview for Next Release" \
    --body "${preview_body}"
else
  gh pr create \
    --title "Changelog Preview for Next Release" \
    --body "${preview_body}" \
    --head "${PREVIEW_BRANCH}" \
    --base "${DEFAULT_BRANCH}"
fi
