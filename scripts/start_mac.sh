#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="finally"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

cd "$PROJECT_DIR"

# Build image if needed or if --build flag passed
if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

# Stop existing container if running (idempotent)
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
elif docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
fi

# Ensure .env file exists
if [[ ! -f .env ]]; then
    echo "Warning: .env file not found. Copy .env.example to .env and configure it."
    echo "Using .env.example as fallback..."
    ENV_FILE=".env.example"
else
    ENV_FILE=".env"
fi

# Run container
echo "Starting FinAlly..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME":/app/db \
    -p "$PORT":"$PORT" \
    --env-file "$ENV_FILE" \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:$PORT"
echo ""

# Open browser on macOS if available
if command -v open &>/dev/null; then
    open "http://localhost:$PORT"
fi
