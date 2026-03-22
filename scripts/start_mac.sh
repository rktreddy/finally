#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CONTAINER_NAME="finally"
IMAGE_NAME="finally"
VOLUME_NAME="finally-data"

# Build if --build flag or image doesn't exist
if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
  echo "Building $IMAGE_NAME Docker image..."
  docker build -t "$IMAGE_NAME" .
fi

# Stop existing container if running
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing $CONTAINER_NAME container..."
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
elif docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
  docker rm "$CONTAINER_NAME"
fi

echo "Starting $CONTAINER_NAME..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p 8000:8000 \
  -v "$VOLUME_NAME":/app/db \
  --env-file .env \
  "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:8000"
echo "To stop: ./scripts/stop_mac.sh"
