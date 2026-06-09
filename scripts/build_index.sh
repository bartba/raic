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

if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

HOST_EMBEDDER_URL="${HOST_EMBEDDER_URL:-http://localhost:${TEI_HOST_PORT:-9091}}"
HOST_VECTOR_INDEX_PATH="${HOST_VECTOR_INDEX_PATH:-${DATA_DIR}/seed_index.npz}"
if [[ "${HOST_VECTOR_INDEX_PATH}" != /* ]]; then
  HOST_VECTOR_INDEX_PATH="${ROOT_DIR}/${HOST_VECTOR_INDEX_PATH}"
fi

"${PYTHON_BIN}" "${SCRIPT_DIR}/build_index.py" \
  --embedder-url "${HOST_EMBEDDER_URL}" \
  --output-path "${HOST_VECTOR_INDEX_PATH}"
