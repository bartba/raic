from pathlib import Path
from types import SimpleNamespace

from fastapi import Response

from main import create_app
from models.request import ClassifyRequest
from routers.classify import classify
from routers.health import ready
from services.vector_store import VectorStore


ROOT_DIR = Path(__file__).resolve().parents[2]


class FakeEmbedder:
    def embed_text(self, text):
        return [1.0, 0.0]


class FakeLLM:
    def generate_json(self, system_prompt, user_prompt):
        return (
            '{"intent":"check_status","slots":{"machine_id":"machine_inspection",'
            '"line_id":"line_packaging"},'
            '"confidence_score":0.91}'
        )


def make_settings(index_path):
    return SimpleNamespace(
        llm_api_url="http://llm.local/v1",
        llm_api_key=None,
        llm_model_name="Qwen3.5-35B-A3B",
        llm_timeout_ms=800,
        llm_max_retries=0,
        embedder_url="http://embedder.local",
        embedder_timeout_ms=800,
        faiss_top_k=1,
        confidence_high=0.85,
        confidence_low=0.60,
        policy_mode="confirm_all",
        intent_schema_path=str(ROOT_DIR / "data" / "intents.yaml"),
        device_schema_path=str(ROOT_DIR / "data" / "devices.yaml"),
        vector_index_path=str(index_path),
        vector_index_use_faiss=False,
        api_auth_token=None,
    )


def write_test_index(path):
    VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=[
            {
                "intent": "check_status",
                "seed_utterance": "상태 확인",
                "is_risky": False,
                "target_scope": "equipment",
                "required_capability": "machine.status.read",
            }
        ],
        use_faiss=False,
    ).save(str(path))


def test_runtime_app_ready_and_classify_with_mock_external_clients(tmp_path):
    index_path = tmp_path / "seed_index.npz"
    write_test_index(index_path)

    app = create_app(
        settings=make_settings(index_path),
        embedder_client=FakeEmbedder(),
        llm_client=FakeLLM(),
        bootstrap_runtime=True,
    )

    ready_response = Response()
    ready_body = ready(SimpleNamespace(app=app), ready_response)

    assert ready_response.status_code == 200
    assert ready_body["status"] == "ok"

    result = classify(
        SimpleNamespace(app=app),
        ClassifyRequest(
            session_id="integration-session",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        ),
    )

    assert result.decision == "confirm"
    assert result.intent == "check_status"
    assert result.slots == {
        "machine_id": "machine_inspection",
        "line_id": "line_packaging",
    }
