#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${CF_PAGES_PROJECT:-amazon-auto-select}"
BRANCH_NAME="${CF_BRANCH:-main}"
NPM_CACHE_DIR="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

cd "$ROOT_DIR/frontend"

echo "== Build frontend =="
npm run build

echo "== Deploy Cloudflare Pages: $PROJECT_NAME / branch $BRANCH_NAME =="
NPM_CONFIG_CACHE="$NPM_CACHE_DIR" npx wrangler pages deploy out --project-name "$PROJECT_NAME" --branch "$BRANCH_NAME"
