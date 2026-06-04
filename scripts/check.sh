#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend syntax check =="
cd "$ROOT_DIR"
python3 -c "from pathlib import Path; files=['app/listing_generator.py','app/routes/listing_projects.py','app/main.py']; [compile(Path(p).read_text(), p, 'exec') for p in files if Path(p).exists()]; print('python syntax ok')"

echo "== Frontend build =="
cd "$ROOT_DIR/frontend"
npm run build

echo "== All checks passed =="
