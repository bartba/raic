from pathlib import Path

from models.request import ClassifyRequest
from models.schema import PolicyDecision, ValidatedResult
from services.normalizer import normalize_text
from services.pipeline import (
    ClassificationPipeline,
    PipelineDependencies,
    build_classify_normalized,
)
from services.policy_engine import decide_policy
from services.schema_manager import load_schema
from services.vector_store import VectorStore


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_real_schema():
    return load_schema(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )


class FakeEmbedder:
    def __init__(self):
        self.texts = []

    def embed_text(self, text):
        self.texts.append(text)
        return [1.0, 0.0]


class FakeLLM:
    def __init__(self):
        self.system_prompt = None
        self.user_prompt = None

    def generate_json(self, system_prompt, user_prompt):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return (
            '{"intent":"check_status","slots":{"machine_id":"machine_inspection",'
            '"line_id":"line_packaging"},'
            '"confidence_score":0.91}'
        )


class TrackingLLM(FakeLLM):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def generate_json(self, system_prompt, user_prompt):
        self.calls += 1
        return super().generate_json(system_prompt, user_prompt)


class FailingEmbedder:
    def embed_text(self, text):
        raise RuntimeError("embedder request timed out")


class FailingLLM:
    def generate_json(self, system_prompt, user_prompt):
        raise RuntimeError("llm request timed out")


class InvalidResultLLM:
    def generate_json(self, system_prompt, user_prompt):
        return '{"intent":"change_model","slots":{},"confidence_score":0.91}'


def make_policy(schema_manager):
    return lambda result: decide_policy(
        result,
        schema_manager.get_intent(result.intent),
        confirm_all=True,
    )


def make_test_vector_store():
    return VectorStore.build(
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        metadata=[
            {
                "intent": "check_status",
                "seed_utterance": "상태 확인",
                "is_risky": False,
                "target_scope": "equipment",
                "required_capability": "machine.status.read",
            },
            {
                "intent": "start_machine",
                "seed_utterance": "장비 시작해",
                "is_risky": True,
                "target_scope": "equipment",
                "required_capability": "machine.start",
            },
        ],
        use_faiss=False,
    )


def test_pipeline_classify_uses_injected_dependencies_and_builds_response():
    calls = []

    def normalize(text):
        calls.append(("normalize", text))
        return "normalized text"

    def classify_normalized(text):
        calls.append(("classify", text))
        return ValidatedResult(
            intent="check_status",
            slots={
                "machine_id": "machine_inspection",
                "line_id": "line_packaging",
            },
            confidence="high",
            confidence_score=0.91,
            is_risky=False,
        )

    def decide_policy(result):
        calls.append(("policy", result.intent))
        return PolicyDecision(decision="confirm", reasons=["confirm_all_enabled"])

    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize,
            classify_normalized=classify_normalized,
            decide_policy=decide_policy,
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        )
    )

    assert calls == [
        ("normalize", "포장 검사기 상태 확인해"),
        ("classify", "normalized text"),
        ("policy", "check_status"),
    ]
    assert response.session_id == "session-1"
    assert response.decision == "confirm"
    assert response.intent == "check_status"
    assert response.slots == {
        "machine_id": "machine_inspection",
        "line_id": "line_packaging",
    }
    assert response.confidence == "high"
    assert response.confidence_score == 0.91
    assert response.is_risky is False
    assert response.policy_reasons == ["confirm_all_enabled"]
    assert response.processing_time_ms >= 0


def test_pipeline_connects_normal_classify_flow_with_mock_external_clients():
    schema_manager = load_real_schema()
    embedder = FakeEmbedder()
    llm = FakeLLM()
    vector_store = make_test_vector_store()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=embedder,
        vector_store=vector_store,
        llm_client=llm,
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        )
    )

    assert response.decision == "confirm"
    assert response.intent == "check_status"
    assert response.slots == {
        "machine_id": "machine_inspection",
        "line_id": "line_packaging",
    }
    assert response.policy_reasons == ["confirm_all_enabled"]
    assert embedder.texts == ["포장 검사기 상태 확인해"]
    assert "Return JSON only" in llm.system_prompt
    assert "Utterance:\n포장 검사기 상태 확인해" in llm.user_prompt
    assert "intent: check_status" in llm.user_prompt
    assert "device_id: machine_inspection" in llm.user_prompt
    assert "line_id: line_packaging" in llm.user_prompt


def test_pipeline_rejects_embedder_failure():
    schema_manager = load_real_schema()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=FailingEmbedder(),
        vector_store=make_test_vector_store(),
        llm_client=FakeLLM(),
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        )
    )

    assert response.decision == "reject"
    assert response.intent == "unknown"
    assert response.policy_reasons == [
        "unknown_intent",
        "validation_failed: embedder request timed out",
    ]


def test_pipeline_rejects_missing_line_before_external_calls():
    schema_manager = load_real_schema()
    embedder = FakeEmbedder()
    llm = TrackingLLM()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=embedder,
        vector_store=make_test_vector_store(),
        llm_client=llm,
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="검사기 상태 확인해",
        )
    )

    assert response.decision == "reject"
    assert response.policy_reasons == [
        "unknown_intent",
        "validation_failed: missing required slot: line_id",
    ]
    assert embedder.texts == []
    assert llm.calls == 0


def test_pipeline_rejects_missing_machine_before_external_calls():
    schema_manager = load_real_schema()
    embedder = FakeEmbedder()
    llm = TrackingLLM()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=embedder,
        vector_store=make_test_vector_store(),
        llm_client=llm,
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 상태 확인해",
        )
    )

    assert response.decision == "reject"
    assert response.policy_reasons == [
        "unknown_intent",
        "validation_failed: missing required slot: machine_id",
    ]
    assert embedder.texts == []
    assert llm.calls == 0


def test_pipeline_rejects_llm_failure():
    schema_manager = load_real_schema()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=FakeEmbedder(),
        vector_store=make_test_vector_store(),
        llm_client=FailingLLM(),
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        )
    )

    assert response.decision == "reject"
    assert response.intent == "unknown"
    assert response.policy_reasons == [
        "unknown_intent",
        "validation_failed: llm request timed out",
    ]


def test_pipeline_rejects_validation_failure():
    schema_manager = load_real_schema()
    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=FakeEmbedder(),
        vector_store=make_test_vector_store(),
        llm_client=InvalidResultLLM(),
        top_k=1,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=make_policy(schema_manager),
        )
    )

    response = pipeline.classify(
        ClassifyRequest(
            session_id="session-1",
            operator_id="operator-1",
            utterance="포장 검사기 상태 확인해",
        )
    )

    assert response.decision == "reject"
    assert response.intent == "change_model"
    assert response.policy_reasons == [
        "validation_failed: "
        "missing required slot: machine_id; "
        "missing required slot: line_id; "
        "missing required slot: model_name"
    ]
