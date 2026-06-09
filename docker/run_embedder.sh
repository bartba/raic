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

TEI_IMAGE="${TEI_IMAGE:-ghcr.io/huggingface/text-embeddings-inference:latest}"
TEI_CONTAINER_NAME="${TEI_CONTAINER_NAME:-tei-embedder}"
TEI_HOST_PORT="${TEI_HOST_PORT:-9091}"
TEI_CONTAINER_PORT="${TEI_CONTAINER_PORT:-80}"
EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID:-Qwen/Qwen3-Embedding-0.6B}"

docker rm -f "${TEI_CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${TEI_CONTAINER_NAME}" \
  --gpus all \
  -p "${TEI_HOST_PORT}:${TEI_CONTAINER_PORT}" \
  "${TEI_IMAGE}" \
  --model-id "${EMBEDDING_MODEL_ID}"
