#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

log(){ echo "[dev-all] $*"; }

# If docker-compose or docker is present, attempt to start infra services
if command -v docker >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
  log "Docker detected — bringing up infra services (redis, minio, chroma) via docker-compose"
  (cd "$ROOT_DIR" && docker compose up -d redis minio chroma) || true

  # Wait for minio (9000) and chroma (8000) to be reachable
  wait_for_http(){
    local host=$1; local port=$2; local path=${3:-/}
    for i in {1..60}; do
      if curl -sS "http://$host:$port$path" >/dev/null 2>&1; then
        return 0
      fi
      sleep 1
    done
    return 1
  }

  log "Waiting for MinIO on port 9000..."
  if wait_for_http localhost 9000 /; then
    log "MinIO reachable"
  else
    log "MinIO did not respond in time — continuing anyway"
  fi

  log "Waiting for Chroma on port 8000..."
  if wait_for_http localhost 8000 /; then
    log "Chroma reachable"
  else
    log "Chroma did not respond in time — continuing anyway"
  fi
else
  log "Docker not found — skipping infra bring-up. Ensure MinIO/Chroma/Redis are running if your tests need them."
fi

# Start local dev apps (backend + frontend)
log "Starting local dev apps via scripts/dev-up.sh"
bash "$ROOT_DIR/scripts/dev-up.sh"

log "All done. Backend + Frontend started. If you used docker compose, infra services are running."
