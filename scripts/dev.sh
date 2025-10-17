#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PY_BACKEND_DIR="$ROOT_DIR/server"
FRONTEND_DIR="$ROOT_DIR/frontend"
mkdir -p "$RUN_DIR"

# Load .env if present
if [ -f "$ROOT_DIR/.env" ]; then
  set -a; . "$ROOT_DIR/.env"; set +a
fi

log() { echo "[dev-simple] $*"; }

# Stop previous pids
for name in backend frontend; do
  pidf="$RUN_DIR/$name.pid"
  if [ -f "$pidf" ]; then
    pid=$(cat "$pidf" || true)
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" || true; sleep 1; kill -9 "$pid" || true
    fi
    rm -f "$pidf"
  fi
done

# Pick backend port (8081 preferred)
BACKEND_PORT=${BACKEND_PORT:-8081}
if ss -ltn "sport = :$BACKEND_PORT" | grep -q ":$BACKEND_PORT"; then
  BACKEND_PORT=8082
fi

log "Starting backend on :$BACKEND_PORT"
python -m pip install -q -e "$PY_BACKEND_DIR" >/dev/null 2>&1 || true
nohup bash -lc "cd '$PY_BACKEND_DIR' && python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT" \
  >"$RUN_DIR/backend.log" 2>&1 & echo $! > "$RUN_DIR/backend.pid"

for i in {1..120}; do
  if curl -sSf http://localhost:$BACKEND_PORT/api/health >/dev/null 2>&1; then
    log "Backend ready at http://localhost:$BACKEND_PORT"
    break
  fi
  sleep 0.5
done

export BACKEND_BASE=${BACKEND_BASE:-http://localhost:$BACKEND_PORT}
log "Starting frontend on :5173 (BACKEND_BASE=$BACKEND_BASE)"
(cd "$FRONTEND_DIR" && npm install)
nohup bash -lc "cd '$FRONTEND_DIR' && npm run dev -- --host 0.0.0.0 --port 5173" \
  >"$RUN_DIR/frontend.log" 2>&1 & echo $! > "$RUN_DIR/frontend.pid"

log "Frontend: http://localhost:5173"
log "Backend:  http://localhost:$BACKEND_PORT"
log "Logs: tail -f $RUN_DIR/backend.log $RUN_DIR/frontend.log"
