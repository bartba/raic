from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_dockerfile_exists_and_uses_x86_requirements():
    dockerfile = ROOT_DIR / "docker" / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")

    assert dockerfile.exists()
    assert "FROM python:3.11-slim" in content
    assert "api/requirements-x86.txt" in content
    assert "pip install --no-cache-dir -r /app/api/requirements-x86.txt" in content
    assert "COPY api /app/api" in content
    assert "COPY data /app/data" in content
    assert "COPY scripts /app/scripts" in content
    assert "EXPOSE 9090" in content
    assert 'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9090"]' in content


def test_docker_build_script_uses_repo_root_context():
    script = ROOT_DIR / "docker" / "build.sh"
    content = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "set -euo pipefail" in content
    assert 'ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"' in content
    assert 'source "${ENV_FILE}"' in content
    assert 'IMAGE_NAME="${IMAGE_NAME:-intent-api}"' in content
    assert 'docker build \\' in content
    assert '-f "${SCRIPT_DIR}/Dockerfile"' in content
    assert '"${ROOT_DIR}"' in content


def test_docker_run_script_runs_intent_api_on_9090_without_reranker():
    script = ROOT_DIR / "docker" / "run.sh"
    content = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "set -euo pipefail" in content
    assert 'ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"' in content
    assert 'source "${ENV_FILE}"' in content
    assert 'LLM_API_URL="${LLM_API_URL:?LLM_API_URL is required}"' in content
    assert 'HOST_PORT="${HOST_PORT:-9090}"' in content
    assert 'CONTAINER_PORT="${CONTAINER_PORT:-9090}"' in content
    assert 'TEI_HOST_PORT="${TEI_HOST_PORT:-9091}"' in content
    assert 'EMBEDDER_URL="${EMBEDDER_URL:-http://host.docker.internal:${TEI_HOST_PORT}}"' in content
    assert 'VECTOR_INDEX_PATH="${VECTOR_INDEX_PATH:-/app/data/seed_index.npz}"' in content
    assert "--add-host=host.docker.internal:host-gateway" in content
    assert '-p "${HOST_PORT}:${CONTAINER_PORT}"' in content
    assert '-v "${DATA_DIR}:/app/data:ro"' in content
    assert '-e "LLM_API_KEY=${LLM_API_KEY:-}"' in content
    assert '-e "EMBEDDER_URL=${EMBEDDER_URL}"' in content
    assert '-e "VECTOR_INDEX_PATH=${VECTOR_INDEX_PATH}"' in content
    assert '-e "VECTOR_INDEX_USE_FAISS=${VECTOR_INDEX_USE_FAISS}"' in content
    assert "reranker" not in content.lower()


def test_docker_run_embedder_script_runs_tei_on_9091_without_reranker():
    script = ROOT_DIR / "docker" / "run_embedder.sh"
    content = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "set -euo pipefail" in content
    assert 'source "${ENV_FILE}"' in content
    assert 'TEI_IMAGE="${TEI_IMAGE:-ghcr.io/huggingface/text-embeddings-inference:latest}"' in content
    assert 'TEI_HOST_PORT="${TEI_HOST_PORT:-9091}"' in content
    assert 'TEI_CONTAINER_PORT="${TEI_CONTAINER_PORT:-80}"' in content
    assert "--gpus all" in content
    assert '-p "${TEI_HOST_PORT}:${TEI_CONTAINER_PORT}"' in content
    assert '--model-id "${EMBEDDING_MODEL_ID}"' in content
    assert "reranker" not in content.lower()


def test_env_example_documents_deploy_settings():
    env_example = ROOT_DIR / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    assert env_example.exists()
    assert "LLM_API_URL=" in content
    assert "LLM_API_KEY=" in content
    assert "API_AUTH_TOKEN=" in content
    assert "EMBEDDER_URL=" in content
    assert "HOST_EMBEDDER_URL=http://localhost:9091" in content
    assert "TEI_HOST_PORT=9091" in content
    assert "EMBEDDING_MODEL_ID=Qwen/Qwen3-Embedding-0.6B" in content
    assert "VECTOR_INDEX_PATH=/app/data/seed_index.npz" in content
    assert "HOST_VECTOR_INDEX_PATH=data/seed_index.npz" in content
    assert "VECTOR_INDEX_USE_FAISS=true" in content
    assert "HOST_PORT=" in content
    assert "CONTAINER_PORT=" in content
