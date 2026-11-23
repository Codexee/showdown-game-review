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
# The win-chance model from the latest GitHub release (28 MB), checked against its SHA-256.
# NO_MODEL=1 ./setup.sh skips it; MODEL_URL=... picks another release asset.
REL="${MODEL_URL:-https://github.com/Codexee/showdown-game-review/releases/latest/download}"
if [ ! -f data/models/current.pt ] && [ "${NO_MODEL:-0}" != 1 ]; then
  echo "== Downloading the win-chance model"
  tmp="data/models/current.pt.part"
  if curl -fsSL -o "$tmp" "$REL/current.pt" && curl -fsSL -o "$tmp.sha256" "$REL/current.pt.sha256"; then
    want=$(awk '{print $1}' "$tmp.sha256")
    if command -v shasum >/dev/null 2>&1; then got=$(shasum -a 256 "$tmp" | awk '{print $1}')
    else got=$(sha256sum "$tmp" | awk '{print $1}'); fi
    if [ -n "$want" ] && [ "$want" = "$got" ]; then
      mv "$tmp" data/models/current.pt
      echo "   installed data/models/current.pt"
    else
      echo "   checksum mismatch: not installed" >&2
      rm -f "$tmp"
    fi
    rm -f "$tmp.sha256"
  else
    rm -f "$tmp" "$tmp.sha256"
    echo "   couldn't download it; the eval bar uses a remaining-HP estimate until a model is added (see README)." >&2
  fi
fi
echo "== Done. Start the app with ./start.sh"
