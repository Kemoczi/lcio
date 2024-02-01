#!/bin/sh

docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker run -d -p "127.0.0.1:$PORT:8000" \
  --restart=always \
  --name "$CONTAINER_NAME" \
  --env DATABASE_URL="$DATABASE_URL" \
  "$CI_REGISTRY_IMAGE:metabotnik_api"
