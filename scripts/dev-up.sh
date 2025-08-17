#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
mkdir -p "$RUN_DIR"

log() { echo "[dev] $*"; }

# Clean previous processes and free ports
if [ -f "$RUN_DIR/backend.pid" ] || [ -f "$RUN_DIR/frontend.pid" ]; then
  bash "$ROOT_DIR/scripts/dev-down.sh" || true
fi
fuser -k 8080/tcp >/dev/null 2>&1 || true
fuser -k 5173/tcp >/dev/null 2>&1 || true

# Start backend in background
log "Starting backend (Ktor) on :8080..."
if [ ! -x "$BACKEND_DIR/gradlew" ]; then
  (cd "$BACKEND_DIR" && gradle wrapper)
fi
nohup bash -lc "cd '$BACKEND_DIR' && ./gradlew run" \
  >"$RUN_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$RUN_DIR/backend.pid"

# Wait for backend health (up to ~120s)
for i in {1..240}; do
  if curl -sSf http://localhost:8080/api/health >/dev/null 2>&1; then
    log "Backend is up (http://localhost:8080)"
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
export BACKEND_BASE=${BACKEND_BASE:-http://localhost:8080}
export PUBLIC_API_BASE=${PUBLIC_API_BASE:-$BACKEND_BASE}
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
log " - Backend:  http://localhost:8080 (health: /api/health, resume: /resume)"
log " - Frontend: http://localhost:5173"
log "Logs: tail -f $RUN_DIR/backend.log $RUN_DIR/frontend.log"
