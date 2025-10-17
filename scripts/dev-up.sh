#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PY_BACKEND_DIR="$ROOT_DIR/server"
FRONTEND_DIR="$ROOT_DIR/frontend"
mkdir -p "$RUN_DIR"

# Load environment from .env if present (not committed)
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi

log() { echo "[dev] $*"; }
# If using Turso/libsql remotely and you want to avoid local SQLite fallback,
# set DATABASE_URL=libsql://... and DATABASE_REQUIRE_REMOTE=1 in your .env


# Clean previous processes and free ports
if [ -f "$RUN_DIR/backend.pid" ] || [ -f "$RUN_DIR/frontend.pid" ]; then
  bash "$ROOT_DIR/scripts/dev-down.sh" || true
fi
fuser -k 5173/tcp >/dev/null 2>&1 || true

# Pick backend port (prefer 8081; fallback to 8082 if occupied)
BACKEND_PORT=${BACKEND_PORT:-}
if [ -z "$BACKEND_PORT" ]; then
  if ss -ltn "sport = :8081" | grep -q ":8081"; then
    BACKEND_PORT=8082
  else
    BACKEND_PORT=8081
  fi
fi

# If we own a previous backend on the chosen port, kill it
if [ -f "$RUN_DIR/backend.pid" ]; then
  fuser -k "$BACKEND_PORT"/tcp >/dev/null 2>&1 || true
fi

# Start worker (Redis queue consumer) in background if REDIS_URL is configured
if [ -n "${REDIS_URL:-}" ]; then
  log "Starting worker (Redis consumer)..."
  nohup bash -lc "cd '$PY_BACKEND_DIR' && REDIS_URL='$REDIS_URL' python -m app.worker" \
    >"$RUN_DIR/worker.log" 2>&1 &
  echo $! > "$RUN_DIR/worker.pid"
else
  log "REDIS_URL not set; worker not started. Set REDIS_URL=redis://localhost:6379/0 to enable."
fi

# Start backend (FastAPI) in background
log "Starting backend (FastAPI) on :$BACKEND_PORT..."
python -m pip install -q -e "$PY_BACKEND_DIR" >/dev/null 2>&1 || true
nohup bash -lc "cd '$PY_BACKEND_DIR' && python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT" \
  >"$RUN_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$RUN_DIR/backend.pid"

# Wait for backend health (up to ~120s)
for i in {1..240}; do
  if curl -sSf http://localhost:$BACKEND_PORT/api/health >/dev/null 2>&1; then
    log "Backend is up (http://localhost:$BACKEND_PORT)"
    break
  fi
  sleep 0.5
  if ! kill -0 $BACKEND_PID >/dev/null 2>&1; then
    log "Backend process exited, check $RUN_DIR/backend.log"
    exit 1
  fi
  if [ $i -eq 240 ]; then
    log "Backend did not become healthy in time. See $RUN_DIR/backend.log"
    exit 1
  fi
done

# Start frontend in background
export BACKEND_BASE=${BACKEND_BASE:-http://localhost:$BACKEND_PORT}
# Do not set PUBLIC_API_BASE by default; let the app use relative URLs + Vite proxy in dev
log "Starting frontend (SvelteKit) on :5173 with BACKEND_BASE=$BACKEND_BASE..."
if [ "${SKIP_NPM_INSTALL:-0}" != "1" ]; then
  (cd "$FRONTEND_DIR" && npm install)
fi
nohup bash -lc "cd '$FRONTEND_DIR' && npm run dev -- --host 0.0.0.0 --port 5173" \
  >"$RUN_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$RUN_DIR/frontend.pid"

# Wait for frontend (up to ~30s)
for i in {1..60}; do
  if curl -sS http://localhost:5173 >/dev/null 2>&1; then
    log "Frontend is up (http://localhost:5173)"
    break
  fi
  sleep 0.5
  if ! kill -0 $FRONTEND_PID >/dev/null 2>&1; then
    log "Frontend process exited, check $RUN_DIR/frontend.log"
    exit 1
  fi
  if [ $i -eq 60 ]; then
    log "Frontend did not respond yet. It may still be compiling. See $RUN_DIR/frontend.log"
  fi
done

log "Both apps started in background."
if [ -f "$RUN_DIR/worker.pid" ]; then
  log " - Worker:   running (see $RUN_DIR/worker.log)"
fi
log " - Backend:  http://localhost:$BACKEND_PORT (health: /api/health)"
log " - Frontend: http://localhost:5173"
log "Logs: tail -f $RUN_DIR/backend.log $RUN_DIR/frontend.log"
