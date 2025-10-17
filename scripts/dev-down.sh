#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
RUN_DIR="$ROOT_DIR/.run"
stop_pid() {
  local name="$1"; local pid_file="$RUN_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file" || true)
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "[dev] Stopping $name (PID $pid)"
      kill "$pid" || true
      sleep 1
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "[dev] Force killing $name"
        kill -9 "$pid" || true
      fi
    fi
    rm -f "$pid_file"
  else
    echo "[dev] No PID file for $name"
  fi
}

stop_pid backend
stop_pid frontend
stop_pid worker

# Also free common ports just in case
fuser -k 8080/tcp >/dev/null 2>&1 || true
fuser -k 5173/tcp >/dev/null 2>&1 || true

echo "[dev] Stopped. Logs in $RUN_DIR/*.log"
