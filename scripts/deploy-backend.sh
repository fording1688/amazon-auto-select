#!/usr/bin/env bash
set -euo pipefail

BACKEND_HOST="${BACKEND_HOST:-root@97.64.29.123}"
BACKEND_DIR="${BACKEND_DIR:-/opt/amazon-auto-select-backend}"
BACKEND_BRANCH="${BACKEND_BRANCH:-main}"
IMAGE_NAME="${BACKEND_IMAGE_NAME:-amazon-auto-select-backend:latest}"
CONTAINER_NAME="${BACKEND_CONTAINER_NAME:-amazon-auto-select-backend}"
PORT_MAPPING="${BACKEND_PORT_MAPPING:-8005:8005}"

echo "== Deploy backend on $BACKEND_HOST =="
ssh "$BACKEND_HOST" "
  set -e
  cd '$BACKEND_DIR'
  if [ -d .git ]; then
    git fetch origin '$BACKEND_BRANCH'
    git checkout '$BACKEND_BRANCH'
    git pull --ff-only origin '$BACKEND_BRANCH'
  else
    echo 'ERROR: backend dir is not a git repo. Clone the repo there once, then rerun this script.'
    exit 2
  fi
  docker build -f Dockerfile.backend -t '$IMAGE_NAME' .
  docker rm -f '$CONTAINER_NAME' >/dev/null 2>&1 || true
  docker run -d --name '$CONTAINER_NAME' --env-file .env -p '$PORT_MAPPING' '$IMAGE_NAME'
  docker ps --filter name='$CONTAINER_NAME' --format '{{.Names}} {{.Status}} {{.Ports}}'
"
