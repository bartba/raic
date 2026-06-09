#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
DATA_DIR="${DATA_DIR:-${ROOT_DIR}/data}"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

IMAGE_NAME="${IMAGE_NAME:-intent-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-intent-api}"
HOST_PORT="${HOST_PORT:-9090}"
CONTAINER_PORT="${CONTAINER_PORT:-9090}"
TEI_HOST_PORT="${TEI_HOST_PORT:-9091}"
EMBEDDER_URL="${EMBEDDER_URL:-http://host.docker.internal:${TEI_HOST_PORT}}"
VECTOR_INDEX_PATH="${VECTOR_INDEX_PATH:-/app/data/seed_index.npz}"
VECTOR_INDEX_USE_FAISS="${VECTOR_INDEX_USE_FAISS:-true}"

LLM_API_URL="${LLM_API_URL:?LLM_API_URL is required}"

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${CONTAINER_NAME}" \
  --add-host=host.docker.internal:host-gateway \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  -v "${DATA_DIR}:/app/data:ro" \
  -e "LLM_API_URL=${LLM_API_URL}" \
  -e "LLM_API_KEY=${LLM_API_KEY:-}" \
  -e "API_AUTH_TOKEN=${API_AUTH_TOKEN:-}" \
  -e "LLM_MODEL_NAME=${LLM_MODEL_NAME:-Qwen3.5-35B-A3B}" \
  -e "LLM_TIMEOUT_MS=${LLM_TIMEOUT_MS:-800}" \
  -e "LLM_MAX_RETRIES=${LLM_MAX_RETRIES:-0}" \
  -e "EMBEDDER_URL=${EMBEDDER_URL}" \
  -e "EMBEDDER_TIMEOUT_MS=${EMBEDDER_TIMEOUT_MS:-800}" \
  -e "FAISS_TOP_K=${FAISS_TOP_K:-10}" \
  -e "CONFIDENCE_HIGH=${CONFIDENCE_HIGH:-0.85}" \
  -e "CONFIDENCE_LOW=${CONFIDENCE_LOW:-0.60}" \
  -e "POLICY_MODE=${POLICY_MODE:-confirm_all}" \
  -e "INTENT_SCHEMA_PATH=${INTENT_SCHEMA_PATH:-/app/data/intents.yaml}" \
  -e "DEVICE_SCHEMA_PATH=${DEVICE_SCHEMA_PATH:-/app/data/devices.yaml}" \
  -e "VECTOR_INDEX_PATH=${VECTOR_INDEX_PATH}" \
  -e "VECTOR_INDEX_USE_FAISS=${VECTOR_INDEX_USE_FAISS}" \
  -e "RAW_UTTERANCE_LOGGING=${RAW_UTTERANCE_LOGGING:-false}" \
  "${IMAGE_NAME}:${IMAGE_TAG}"
