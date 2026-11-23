#!/usr/bin/env bash
# Start showdown-game-review on this computer and open it in the browser.
#   ./start.sh            -> http://127.0.0.1:8765
#   PORT=9000 ./start.sh  -> another port (the userscript expects 8765 unless you change it)
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ] || [ ! -f web/dist/index.html ]; then ./setup.sh; fi
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}"
(
  sleep 2
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi
) >/dev/null 2>&1 &
echo "showdown-game-review: ${URL}  (Ctrl-C to stop)"
exec uv run --no-dev uvicorn server.app:app --host 127.0.0.1 --port "$PORT"
