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

TEI_BASE_IMAGE="${TEI_BASE_IMAGE:-ghcr.io/huggingface/text-embeddings-inference:cuda-1.8}"
TEI_IMAGE="${TEI_IMAGE:-raic-tei-embedder:cuda-1.8}"
TEI_CA_CERT_PATH="${TEI_CA_CERT_PATH:?TEI_CA_CERT_PATH is required}"

if [ ! -f "${TEI_CA_CERT_PATH}" ]; then
  echo "TEI_CA_CERT_PATH does not exist: ${TEI_CA_CERT_PATH}" >&2
  exit 1
fi

BUILD_CONTEXT="$(mktemp -d)"
cleanup() {
  rm -rf "${BUILD_CONTEXT}"
}
trap cleanup EXIT

cp "${SCRIPT_DIR}/Dockerfile.tei" "${BUILD_CONTEXT}/Dockerfile"
cp "${TEI_CA_CERT_PATH}" "${BUILD_CONTEXT}/DigitalCity.crt"

docker build \
  --build-arg "TEI_BASE_IMAGE=${TEI_BASE_IMAGE}" \
  -t "${TEI_IMAGE}" \
  "${BUILD_CONTEXT}"
