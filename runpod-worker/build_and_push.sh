#!/bin/bash
# Build and push the TRELLIS.2 RunPod worker image.
# Requires: docker login -u tuxeai  (run this first).
set -euo pipefail

DOCKER_USERNAME="${DOCKER_USERNAME:-tuxeai}"
IMAGE_NAME="trellis2-runpod-worker"
TAG="${TAG:-v1.0}"
FULL_IMAGE="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

echo "Building ${FULL_IMAGE} (linux/amd64)..."
docker build --platform linux/amd64 -t "${FULL_IMAGE}" -f Dockerfile .

echo "Pushing ${FULL_IMAGE}..."
docker push "${FULL_IMAGE}"

echo "Done: ${FULL_IMAGE}"
