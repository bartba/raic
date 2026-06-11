from pydantic import ValidationError

from models.common import Confidence, Decision
from models.request import ClassifyRequest
from models.response import ClassifyResponse
from models.schema import (
    Candidate,
    ComponentDef,
    DeviceDef,
    IntentDef,
    PolicyDecision,
    SlotDef,
    ValidatedResult,
)


def test_classify_request_accepts_valid_payload():
    request = ClassifyRequest(
        session_id="ses-001",
        operator_id="op-042",
        utterance="3번 컨베이어 속도 200으로 올려",
    )

    assert request.utterance == "3번 컨베이어 속도 200으로 올려"


def test_classify_request_rejects_empty_utterance():
    try:
        ClassifyRequest(session_id="ses-001", operator_id="op-042", utterance="")
    except ValidationError:
        return

    raise AssertionError("empty utterance should be rejected")


def test_classify_response_accepts_prd_shape():
    response = ClassifyResponse(
        session_id="ses-001",
        decision="confirm",
        intent="set_speed",
        slots={
            "machine_id": "conveyor_3",
            "line_id": "line_1",
            "value": 200,
            "unit": "rpm",
        },
        confidence="high",
        confidence_score=0.92,
        is_risky=False,
        policy_reasons=["confirm_all_control_commands"],
        processing_time_ms=185,
    )

    assert response.decision == "confirm"
    assert response.slots["value"] == 200


def test_schema_models_can_be_created():
    slot = SlotDef(name="machine_id", type="string", required=True)
    intent = IntentDef(
        name="set_speed",
        description="장비 속도 설정",
        target_scope="component",
        required_capability="robot.speed.set",
        is_risky=False,
        slots=[slot],
        allowed_decisions=["confirm", "reject", "execute"],
        seed_utterances=["컨베이어 속도 올려"],
    )
    component = ComponentDef(
        id="robot",
        aliases=["로봇"],
        capabilities=["robot.speed.set"],
    )
    device = DeviceDef(
        id="conveyor_3",
        line_id="line_1",
        aliases=["3번 컨베이어"],
        capabilities=["machine.status.read"],
        components=[component],
    )
    candidate = Candidate(intent="set_speed", score=0.91, seed_utterance="속도 올려")
    validated = ValidatedResult(
        intent="set_speed",
        slots={"machine_id": "conveyor_3", "line_id": "line_1"},
        confidence="high",
        confidence_score=0.91,
    )
    decision = PolicyDecision(decision="confirm", reasons=["confirm_all_control_commands"])

    assert intent.slots[0].name == "machine_id"
    assert intent.required_capability == "robot.speed.set"
    assert device.aliases == ["3번 컨베이어"]
    assert device.components[0].id == "robot"
    assert candidate.score == 0.91
    assert validated.is_valid is True
    assert validated.errors == []
    assert decision.reasons == ["confirm_all_control_commands"]


def test_common_types_are_shared():
    decision: Decision = "confirm"
    confidence: Confidence = "high"

    assert decision == "confirm"
    assert confidence == "high"
