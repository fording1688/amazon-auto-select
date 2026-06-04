# Release Scripts

These scripts reduce repeated manual steps.

## Local check

```bash
./scripts/check.sh
```

Runs backend Python syntax checks and frontend `npm run build`.

## Deploy frontend only

```bash
./scripts/deploy-frontend.sh
```

Defaults:

- Cloudflare Pages project: `amazon-auto-select`
- Branch: `main`

Override when needed:

```bash
CF_BRANCH=codex/dockerize-amazon-auto-select ./scripts/deploy-frontend.sh
```

## Deploy backend only

```bash
./scripts/deploy-backend.sh
```

Defaults:

- Host: `root@97.64.29.123`
- Directory: `/opt/amazon-auto-select-backend`
- Branch: `codex/dockerize-amazon-auto-select`
- Container: `amazon-auto-select-backend`

Override when migrating hosts:

```bash
BACKEND_HOST=root@NEW_IP BACKEND_DIR=/opt/amazon-auto-select-backend ./scripts/deploy-backend.sh
```

The backend directory on the server should be a git checkout of this repo and should contain its own `.env`.

## Check, commit, and push

```bash
./scripts/release.sh "Your commit message"
```

This runs checks, commits staged project files, and pushes the current branch.
