#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

IMAGE_NAME="${IMAGE_NAME:-intent-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker build \
  --build-arg "HTTP_PROXY=${HTTP_PROXY:-}" \
  --build-arg "HTTPS_PROXY=${HTTPS_PROXY:-}" \
  --build-arg "NO_PROXY=${NO_PROXY:-}" \
  -f "${SCRIPT_DIR}/Dockerfile" \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${ROOT_DIR}"
