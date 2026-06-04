#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${GIT_REMOTE:-origin}"
BRANCH="${GIT_BRANCH:-$(git -C "$ROOT_DIR" branch --show-current)}"
MESSAGE="${1:-Update amazon auto select}"

cd "$ROOT_DIR"

echo "== Check =="
"$ROOT_DIR/scripts/check.sh"

echo "== Commit =="
git status --short
git add app frontend database docs scripts README.md Dockerfile.backend requirements.txt
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "$MESSAGE"
fi

echo "== Push =="
git push "$REMOTE" "$BRANCH"

echo "== Done =="
