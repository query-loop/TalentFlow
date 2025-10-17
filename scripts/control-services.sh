#!/usr/bin/env bash
set -euo pipefail

# Control script to start/stop/restart/status all project services.
# Usage: control-services.sh start|stop|restart|status

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 start|stop|restart|status"
  exit 2
fi

cmd="$1"

use_compose=false
if [ -f docker-compose.yml ] || ls docker-compose.* >/dev/null 2>&1; then
  use_compose=true
fi

# helper: wait for a TCP port to respond with optional HTTP success (accept 200 or 404 for some services)
wait_for_http() {
  local url="$1"
  local timeout=${2:-30}
  echo "Waiting for $url (timeout ${timeout}s)"
  local start=$(date +%s)
  while true; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" >/tmp/.cf_code 2>/dev/null; then
      code=$(cat /tmp/.cf_code)
      if [ "$code" = "200" ] || [ "$code" = "404" ]; then
        echo "$url responded with HTTP $code"
        return 0
      fi
    fi
    now=$(date +%s)
    if [ $((now - start)) -ge $timeout ]; then
      echo "Timed out waiting for $url"
      return 1
    fi
    sleep 1
  done
}


case "$cmd" in
  start)
    if [ "$use_compose" = true ]; then
      echo "Bringing up docker compose services..."
      docker compose pull || true
      if docker compose up -d --build; then
        docker compose ps
        # wait for frontend, backend and chroma mapped ports
        wait_for_http "http://localhost:5174/" 40 || echo "Frontend didn't respond in time"
        wait_for_http "http://localhost:9002/api/health" 40 || wait_for_http "http://localhost:9002/" 20 || echo "Backend didn't respond in time"
        # Chroma may return 200 or 404 root; accept either if reachable
        wait_for_http "http://localhost:8000/" 30 || echo "Chroma didn't respond in time"
      else
        echo "docker compose up failed. Falling back to starting frontend/backend individually."
        # Try make targets first
        if command -v make >/dev/null 2>&1 && make -n dev-up >/dev/null 2>&1; then
          make dev-up || true
        else
          # Start backend (server) if present
          if [ -d backend ] && [ -f backend/build.gradle.kts ]; then
            echo "No compose. Starting backend via Gradle (if configured)..."
            (cd backend && ./gradlew bootRun) &
          elif [ -d server ] && [ -f server/pyproject.toml ]; then
            echo "Starting Python server..."
            (cd server && bash -lc "pip install -U pip && pip install -e . && uvicorn app.main:app --host 0.0.0.0 --port 8080") &
          fi

          # Start frontend
          if [ -d frontend ] && [ -f frontend/package.json ]; then
            echo "Starting frontend..."
            (cd frontend && if command -v pnpm >/dev/null 2>&1; then PM=pnpm; elif command -v yarn >/dev/null 2>&1; then PM=yarn; else PM=npm; fi && $PM install && $PM run dev -- --host 0.0.0.0) &
          fi

          echo "Fallback start invoked; check process list or logs."
        fi
      fi
    elif command -v make >/dev/null 2>&1 && make -n dev >/dev/null 2>&1; then
      echo "Running: make dev"
      make dev
    elif [ -f package.json ]; then
      echo "Starting frontend (npm/yarn/pnpm)..."
      if command -v pnpm >/dev/null 2>&1; then PM=pnpm
      elif command -v yarn >/dev/null 2>&1; then PM=yarn
      else PM=npm
      fi
      $PM install
      if grep -q '"dev":' package.json; then
        $PM run dev
      else
        $PM start
      fi
    else
      echo "No recognized runner (docker-compose, make, or package.json)."
      exit 3
    fi
    ;;
  stop)
    if [ "$use_compose" = true ]; then
      echo "Stopping docker compose services..."
      docker compose down --volumes --remove-orphans
    elif command -v make >/dev/null 2>&1 && make -n down >/dev/null 2>&1; then
      echo "Running: make down"
      make down
    else
      echo "No recognized runner to stop services. If you started services manually, stop them accordingly."
      exit 3
    fi
    ;;
  restart)
    "$0" stop
    sleep 2
    "$0" start
    ;;
  status)
    if [ "$use_compose" = true ]; then
      docker compose ps
    else
      echo "No docker-compose; check process list or make targets for status."
    fi
    ;;
  *)
    echo "Unknown command: $cmd"
    echo "Usage: $0 start|stop|restart|status"
    exit 2
    ;;
esac

exit 0
