#!/usr/bin/env bash
# Launch the entire stack on Linux/macOS:
#   1. Backend  (FastAPI / uvicorn on :8080)
#   2. Tunnel   (ngrok -> :8080, needed only for real phone calls)
#   3. Frontend (Next.js on :3000)
#
# Unlike all-start.bat (which opens three windows), this runs all three as
# background jobs in ONE terminal, tags their output, and stops everything
# together when you press Ctrl+C.

set -euo pipefail

# Always run from the directory this script lives in.
cd "$(dirname "$0")"

VENV_DIR=".venv"
PIDS=()

# --- Cleanup: kill all child services on Ctrl+C / exit -----------------------
cleanup() {
  echo ""
  echo "[stop] Shutting down the stack..."
  for pid in "${PIDS[@]}"; do
    # Kill the process group so child processes (uvicorn workers, next) die too.
    kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "[stop] Done."
}
trap cleanup INT TERM EXIT

# --- 1. Backend --------------------------------------------------------------
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[start] $VENV_DIR not found. Creating it and installing dependencies..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

echo "[start] Launching uvicorn on http://0.0.0.0:8080"
setsid "$VENV_DIR/bin/python" -m uvicorn app:app \
  --host 0.0.0.0 --port 8080 --log-level info \
  2>&1 | sed 's/^/[backend] /' &
PIDS+=($!)

sleep 3

# --- 2. Tunnel (optional, needs ngrok installed) -----------------------------
if command -v ngrok >/dev/null 2>&1; then
  echo "[tunnel] Forwarding saloon-untried-maturely.ngrok-free.dev -> localhost:8080"
  setsid ngrok http 8080 --url=https://saloon-untried-maturely.ngrok-free.dev --log=stdout 2>&1 | sed 's/^/[tunnel] /' &
  PIDS+=($!)
else
  echo "[tunnel] ngrok not found on PATH - skipping tunnel."
  echo "[tunnel] Install from https://ngrok.com/download if you need real phone calls."
fi

sleep 2

# --- 3. Frontend -------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  echo "[web] Node.js not found on PATH. Install from https://nodejs.org" >&2
  exit 1
fi

if [ ! -d "web/node_modules" ]; then
  echo "[web] node_modules missing - running npm install (first run only)..."
  ( cd web && npm install )
fi

echo "[web] Starting Next.js on http://localhost:3000"
setsid bash -c 'cd web && npm run dev' 2>&1 | sed 's/^/[web] /' &
PIDS+=($!)

# --- Summary -----------------------------------------------------------------
cat <<'EOF'

================================================================
Stack is starting up:
  - Backend  : http://localhost:8080
  - Tunnel   : ngrok (see [tunnel] lines above for the public URL)
  - Frontend : http://localhost:3000   (wait ~5s for it to compile)

Press Ctrl+C to stop ALL three services.
================================================================
EOF

# Wait until interrupted; cleanup() handles shutdown.
wait
