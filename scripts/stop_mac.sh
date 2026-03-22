#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="finally"

if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
  echo "Stopping $CONTAINER_NAME..."
  docker stop "$CONTAINER_NAME"
  docker rm "$CONTAINER_NAME"
  echo "$CONTAINER_NAME stopped. Data volume preserved."
elif docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
  docker rm "$CONTAINER_NAME"
  echo "Removed stopped $CONTAINER_NAME container. Data volume preserved."
else
  echo "No $CONTAINER_NAME container found."
fi
