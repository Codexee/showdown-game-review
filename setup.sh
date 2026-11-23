#!/usr/bin/env bash
# One-time setup for showdown-game-review: Python packages (uv installs Python 3.13 itself),
# the web app build, and the data folder. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing $1. $2" >&2
    exit 1
  fi
}
need uv   "Install it: curl -LsSf https://astral.sh/uv/install.sh | sh   (https://docs.astral.sh/uv/)"
need node "Install Node.js 20 or newer: https://nodejs.org"
need npm  "It comes with Node.js: https://nodejs.org"
need git  "Install git: https://git-scm.com"

echo "== Python packages (first run downloads PyTorch, a few hundred MB)"
uv sync --no-dev

echo "== Web app"
(cd web && npm ci --no-audit --no-fund --loglevel=error && npm run build >/dev/null)

mkdir -p data/models
if [ ! -f data/models/current.pt ]; then
  echo "== No model installed yet: the eval bar uses a remaining-HP estimate until you add one (see README)."
fi
echo "== Done. Start the app with ./start.sh"
