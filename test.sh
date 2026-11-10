#!/usr/bin/env bash
# Local smoke test: /health + one /demo call. Key is fetched fresh from the
# surrogate helper and never printed or written to disk.
set -euo pipefail
cd "$(dirname "$0")"
export OPENROUTER_API_KEY="$(python3 ~/workspace/skills/openrouter/bin/print_surrogate.py)"
python3 app.py &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
sleep 1
echo "== /health =="
curl -s http://127.0.0.1:8080/health; echo
echo "== /demo =="
curl -s -X POST http://127.0.0.1:8080/demo \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"用一句话介绍你自己。"}'; echo
