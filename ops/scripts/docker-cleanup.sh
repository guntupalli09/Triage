#!/usr/bin/env bash
set -euo pipefail

LOG="/var/log/docker-cleanup.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "========== Docker Cleanup Started =========="

log "--- Disk usage BEFORE cleanup ---"
docker system df 2>&1 | tee -a "$LOG"

log "--- Listing running containers (these will NOT be touched) ---"
docker ps --format '{{.ID}} {{.Image}} {{.Names}}' 2>&1 | tee -a "$LOG"

RUNNING_IMAGES=$(docker ps -q | xargs -r docker inspect --format '{{.Image}}' | sort -u)
log "Protected images (in use by running containers):"
echo "$RUNNING_IMAGES" | tee -a "$LOG"

log "--- Removing stopped containers ---"
docker container prune -f 2>&1 | tee -a "$LOG"

log "--- Removing dangling images ---"
docker image prune -f 2>&1 | tee -a "$LOG"

log "--- Removing unused images (not referenced by any container) ---"
docker image prune -a -f 2>&1 | tee -a "$LOG"

log "--- Removing dangling and unused build cache ---"
docker builder prune -f 2>&1 | tee -a "$LOG"

log "--- Removing unused networks ---"
docker network prune -f 2>&1 | tee -a "$LOG"

log "--- Verifying running containers are still up ---"
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}' 2>&1 | tee -a "$LOG"

log "--- Verifying named volumes are intact ---"
docker volume ls 2>&1 | tee -a "$LOG"

log "--- Disk usage AFTER cleanup ---"
docker system df 2>&1 | tee -a "$LOG"

log "========== Docker Cleanup Completed =========="
