#!/usr/bin/env bash
set -euo pipefail

# Only deployment workflows are owned by this fork. Application conflicts must
# still stop the update so local behavior is never silently overwritten.
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Upstream sync requires a clean checkout.' >&2
  exit 1
fi
git fetch "${UPSTREAM_REPOSITORY:-https://github.com/moesnow/March7thAssistant.git}" "${UPSTREAM_BRANCH:-main}"
if git merge-base --is-ancestor FETCH_HEAD HEAD; then
  echo 'Upstream is already merged.'
  exit 0
fi

if ! git merge --no-ff --no-commit FETCH_HEAD; then
  # A missing MERGE_HEAD is a Git error, not a resolvable content conflict.
  git rev-parse --verify MERGE_HEAD >/dev/null
fi

# Clear the index entries first: restore alone cannot handle an upstream
# modification of a workflow that this fork deleted. This also drops newly
# added upstream workflows while restoring every local workflow unchanged.
git rm -r -f --ignore-unmatch -- .github/workflows
git restore --source=HEAD --staged --worktree -- .github/workflows
if [[ -n "$(git diff --name-only --diff-filter=U)" ]]; then
  git diff --name-only --diff-filter=U
  git merge --abort
  echo 'Upstream application conflicts need review; production remains unchanged.' >&2
  exit 1
fi
git commit -m 'Merge upstream updates; retain custom deployment workflows'
