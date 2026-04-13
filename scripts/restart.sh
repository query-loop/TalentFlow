#!/usr/bin/env bash
# Restart all TalentFlow services (backend, frontend, and infra if using Docker).
# Works in local dev and GitHub Codespaces.
#
# Usage:
#   bash scripts/restart.sh           # auto-detect Docker vs local
#   bash scripts/restart.sh --docker  # force Docker compose path
#   bash scripts/restart.sh --local   # force local dev (dev-down + dev-up)

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { echo "[restart] $*"; }

# ── Parse arguments ──────────────────────────────────────────────────────────
MODE="auto"
for arg in "$@"; do
  case "$arg" in
    --docker) MODE="docker" ;;
    --local)  MODE="local"  ;;
    *) echo "Usage: $0 [--docker|--local]"; exit 2 ;;
  esac
done

# ── Auto-detect mode ──────────────────────────────────────────────────────────
if [ "$MODE" = "auto" ]; then
  if command -v docker >/dev/null 2>&1 && [ -f "$ROOT_DIR/docker-compose.yml" ]; then
    # Only use Docker mode if compose services are actually running
    if docker compose ps -q 2>/dev/null | grep -q .; then
      MODE="docker"
    else
      MODE="local"
    fi
  else
    MODE="local"
  fi
fi

log "Restart mode: $MODE"

# ── Docker compose restart ────────────────────────────────────────────────────
if [ "$MODE" = "docker" ]; then
  log "Stopping docker compose services (preserving volumes)..."
  docker compose stop
  sleep 2
  log "Starting docker compose services..."
  docker compose up -d --build
  docker compose ps
  log "All docker compose services restarted."
  log " - Frontend: http://localhost:5174"
  log " - Backend:  http://localhost:9002"
  exit 0
fi

# ── Local dev restart ─────────────────────────────────────────────────────────
log "Stopping existing local dev processes..."
bash "$ROOT_DIR/scripts/dev-down.sh"

sleep 1

log "Starting local dev processes..."
bash "$ROOT_DIR/scripts/dev-up.sh"
