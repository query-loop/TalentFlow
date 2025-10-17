#!/usr/bin/env bash
# Check required services (minio, chroma, celery_worker) are running via docker-compose
# If any service is not running, pull images and start docker-compose up -d for those services.

set -euo pipefail
cd "$(dirname "$0")/.."

REQUIRED=(minio chroma celery_worker flower)
MISSING=()

for svc in "${REQUIRED[@]}"; do
  status=$(docker-compose ps -q "$svc" 2>/dev/null || true)
  if [ -z "$status" ]; then
    MISSING+=("$svc")
  fi
done

if [ ${#MISSING[@]} -eq 0 ]; then
  echo "All required services already present."
  docker-compose ps
  exit 0
fi

echo "Missing services: ${MISSING[*]}"
echo "Pulling images and starting services: ${MISSING[*]}"

docker-compose pull "${MISSING[@]}" || true
# Start missing services
for svc in "${MISSING[@]}"; do
  docker-compose up -d "$svc"
done

echo "Started missing services."
docker-compose ps
