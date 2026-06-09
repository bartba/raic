from types import SimpleNamespace

from fastapi import HTTPException

from models.request import ClassifyRequest
from models.response import ClassifyResponse
from routers.classify import classify


class FakePipeline:
    def __init__(self):
        self.request = None

    def classify(self, request):
        self.request = request
        return ClassifyResponse(
            session_id=request.session_id,
            decision="confirm",
            intent="check_status",
            slots={"machine_id": "machine_inspection"},
            confidence="high",
            confidence_score=0.91,
            is_risky=False,
            policy_reasons=["confirm_all_enabled"],
            processing_time_ms=3,
        )


class TimeoutPipeline:
    def classify(self, request):
        return ClassifyResponse(
            session_id=request.session_id,
            decision="reject",
            intent="unknown",
            slots={},
            confidence="low",
            confidence_score=0.0,
            is_risky=False,
            policy_reasons=["validation_failed: llm request timed out"],
            processing_time_ms=3,
        )


class FakeMetric:
    def __init__(self):
        self.calls = []

    def labels(self, **labels):
        self.calls.append(labels)
        return self

    def inc(self):
        self.calls.append("inc")


def make_request_with_pipeline(pipeline=None):
    state = SimpleNamespace()
    if pipeline is not None:
        state.pipeline = pipeline
    return SimpleNamespace(app=SimpleNamespace(state=state))


def test_classify_router_calls_pipeline():
    pipeline = FakePipeline()
    payload = ClassifyRequest(
        session_id="session-1",
        operator_id="operator-1",
        utterance="포장 검사기 상태 확인해",
    )

    response = classify(make_request_with_pipeline(pipeline), payload)

    assert pipeline.request == payload
    assert response.decision == "confirm"
    assert response.intent == "check_status"
    assert response.slots == {"machine_id": "machine_inspection"}


def test_classify_router_rejects_when_pipeline_is_not_ready():
    payload = ClassifyRequest(
        session_id="session-1",
        operator_id="operator-1",
        utterance="포장 검사기 상태 확인해",
    )

    try:
        classify(make_request_with_pipeline(), payload)
    except HTTPException as error:
        assert error.status_code == 503
        assert error.detail == "classification pipeline is not ready"
        return

    raise AssertionError("missing pipeline should fail")


def test_classify_router_records_timeout_metric():
    decision_metric = FakeMetric()
    timeout_metric = FakeMetric()
    request = make_request_with_pipeline(TimeoutPipeline())
    request.app.state.metrics = {
        "decision_count": decision_metric,
        "timeout_count": timeout_metric,
    }
    payload = ClassifyRequest(
        session_id="session-1",
        operator_id="operator-1",
        utterance="포장 검사기 상태 확인해",
    )

    response = classify(request, payload)

    assert response.decision == "reject"
    assert decision_metric.calls == [{"decision": "reject", "intent": "unknown"}, "inc"]
    assert timeout_metric.calls == [{"source": "llm"}, "inc"]
