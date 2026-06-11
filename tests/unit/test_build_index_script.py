from pathlib import Path

from scripts.build_index import build_mock_embeddings, main
from services.vector_store import VectorStore


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_build_mock_embeddings_are_deterministic():
    first = build_mock_embeddings(["상태 확인해", "장비 시작해"])
    second = build_mock_embeddings(["상태 확인해", "장비 시작해"])

    assert first == second
    assert len(first) == 2
    assert len(first[0]) == 16


def test_build_index_script_saves_mock_index(tmp_path, monkeypatch):
    output_path = tmp_path / "seed_index.npz"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_index.py",
            "--intent-path",
            str(ROOT_DIR / "data" / "intents.yaml"),
            "--device-path",
            str(ROOT_DIR / "data" / "devices.yaml"),
            "--output-path",
            str(output_path),
            "--mock-embeddings",
            "--no-faiss",
        ],
    )

    assert main() == 0

    store = VectorStore.load(str(output_path), use_faiss=False)
    assert len(store.metadata) >= 100
    assert {"intent", "seed_utterance", "required_capability"}.issubset(
        store.metadata[0]
    )


def test_build_index_shell_script_loads_env_and_uses_host_embedder_url():
    script = ROOT_DIR / "scripts" / "build_index.sh"
    content = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "set -euo pipefail" in content
    assert 'source "${ENV_FILE}"' in content
    assert 'HOST_EMBEDDER_URL="${HOST_EMBEDDER_URL:-http://localhost:${TEI_HOST_PORT:-9091}}"' in content
    assert 'HOST_VECTOR_INDEX_PATH="${HOST_VECTOR_INDEX_PATH:-${DATA_DIR}/seed_index.npz}"' in content
    assert '--embedder-url "${HOST_EMBEDDER_URL}"' in content
    assert '--output-path "${HOST_VECTOR_INDEX_PATH}"' in content
    assert '"$@"' in content
