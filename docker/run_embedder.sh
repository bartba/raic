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

TEI_IMAGE="${TEI_IMAGE:-raic-tei-embedder:cuda-1.8}"
TEI_CONTAINER_NAME="${TEI_CONTAINER_NAME:-tei-embedder}"
TEI_HOST_PORT="${TEI_HOST_PORT:-9091}"
TEI_CONTAINER_PORT="${TEI_CONTAINER_PORT:-80}"
TEI_GPU_DEVICE="${TEI_GPU_DEVICE:-device=1}"
EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID:-BAAI/bge-m3}"
TEI_DTYPE="${TEI_DTYPE:-float16}"
TEI_POOLING="${TEI_POOLING:-cls}"

docker rm -f "${TEI_CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${TEI_CONTAINER_NAME}" \
  --gpus "${TEI_GPU_DEVICE}" \
  -p "${TEI_HOST_PORT}:${TEI_CONTAINER_PORT}" \
  -e "HTTP_PROXY=${HTTP_PROXY:-}" \
  -e "HTTPS_PROXY=${HTTPS_PROXY:-}" \
  -e "NO_PROXY=${NO_PROXY:-localhost,127.0.0.1}" \
  -e "http_proxy=${http_proxy:-${HTTP_PROXY:-}}" \
  -e "https_proxy=${https_proxy:-${HTTPS_PROXY:-}}" \
  -e "no_proxy=${no_proxy:-${NO_PROXY:-localhost,127.0.0.1}}" \
  -e "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" \
  -e "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" \
  "${TEI_IMAGE}" \
  --model-id "${EMBEDDING_MODEL_ID}" \
  --dtype "${TEI_DTYPE}" \
  --pooling "${TEI_POOLING}" \
  --max-batch-tokens 65536 \
  --auto-truncate
