#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-intent-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker build \
  -f "${SCRIPT_DIR}/Dockerfile" \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${ROOT_DIR}"
