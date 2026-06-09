from pathlib import Path
from types import SimpleNamespace

from models.request import ClassifyRequest
from services.bootstrap import BootstrapError, build_runtime_components
from services.schema_manager import load_schema
from services.vector_store import VectorStore


ROOT_DIR = Path(__file__).resolve().parents[2]


class FakeEmbedder:
    def embed_text(self, text):
        return [1.0, 0.0]


class FakeLLM:
    def generate_json(self, system_prompt, user_prompt):
        return (
            '{"intent":"check_status","slots":{"machine_id":"machine_inspection"},'
            '"confidence_score":0.91}'
        )


def make_settings(index_path, **overrides):
    values = {
        "llm_api_url": "http://llm.local/v1",
        "llm_api_key": None,
        "llm_model_name": "Qwen3.5-35B-A3B",
        "llm_timeout_ms": 800,
        "llm_max_retries": 0,
        "embedder_url": "http://embedder.local",
        "embedder_timeout_ms": 800,
        "faiss_top_k": 1,
        "confidence_high": 0.85,
        "confidence_low": 0.60,
        "policy_mode": "confirm_all",
        "intent_schema_path": str(ROOT_DIR / "data" / "intents.yaml"),
        "device_schema_path": str(ROOT_DIR / "data" / "devices.yaml"),
        "vector_index_path": str(index_path),
        "vector_index_use_faiss": False,
        "api_auth_token": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def write_test_index(path):
    VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=[
            {
                "intent": "check_status",
                "seed_utterance": "검사기 상태 확인",
                "is_risky": False,
                "target_scope": "equipment",
                "required_capability": "machine.status.read",
                "target_component_type": None,
            }
        ],
        use_faiss=False,
    ).save(str(path))


def test_build_runtime_components_wires_pipeline_from_settings(tmp_path):
    index_path = tmp_path / "seed_index.npz"
    write_test_index(index_path)

    components = build_runtime_components(
        make_settings(index_path),
        embedder_client=FakeEmbedder(),
        llm_client=FakeLLM(),
    )

    response = components.pipeline.classify(
        ClassifyRequest(
            utterance="검사기 상태 확인해",
            session_id="session-1",
            operator_id="operator-1",
        )
    )

    assert components.schema_manager.get_intent("check_status") is not None
    assert components.vector_store.dimension == 2
    assert response.decision == "confirm"
    assert response.intent == "check_status"


def test_build_runtime_components_rejects_invalid_policy_mode(tmp_path):
    index_path = tmp_path / "seed_index.npz"

    try:
        build_runtime_components(
            make_settings(index_path, policy_mode="unknown"),
            schema_manager=load_schema(
                str(ROOT_DIR / "data" / "intents.yaml"),
                str(ROOT_DIR / "data" / "devices.yaml"),
            ),
            vector_store=VectorStore.build(
                embeddings=[[1.0, 0.0]],
                metadata=[{"intent": "check_status", "seed_utterance": "검사기 상태"}],
                use_faiss=False,
            ),
            embedder_client=FakeEmbedder(),
            llm_client=FakeLLM(),
        )
    except BootstrapError as error:
        assert str(error) == "unsupported POLICY_MODE: unknown"
        return

    raise AssertionError("invalid policy mode should fail bootstrap")
