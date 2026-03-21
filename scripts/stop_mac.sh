#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="finally-app"

# Stop and remove container (idempotent — safe to run if already stopped)
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo "Stopping FinAlly..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
fi

if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
    echo "Container removed."
else
    echo "No running FinAlly container found."
fi

echo "Note: Data volume 'finally-data' is preserved. Use 'docker volume rm finally-data' to delete it."
