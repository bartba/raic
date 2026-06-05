from typing import List, Optional

from models.schema import IntentDef, SlotDef, ValidatedResult
from services.policy_engine import decide_policy


def make_intent(
    name: str = "set_light_intensity",
    is_risky: bool = False,
    allowed_decisions: Optional[List[str]] = None,
) -> IntentDef:
    return IntentDef(
        name=name,
        description="test intent",
        target_scope="component",
        target_component_type="led_light",
        required_capability="light.intensity.set",
        is_risky=is_risky,
        allowed_decisions=allowed_decisions or ["confirm", "reject", "execute"],
        slots=[
            SlotDef(name="machine_id", type="string", required=True),
            SlotDef(name="value", type="integer", required=True, min=0, max=255),
        ],
        seed_utterances=["조명 100으로 맞춰"],
    )


def make_result(
    intent: str = "set_light_intensity",
    confidence: str = "high",
    confidence_score: float = 0.92,
    is_risky: bool = False,
    errors: Optional[List[str]] = None,
) -> ValidatedResult:
    return ValidatedResult(
        intent=intent,
        slots={"machine_id": "machine_inspection", "value": 100},
        confidence=confidence,
        confidence_score=confidence_score,
        is_risky=is_risky,
        errors=errors or [],
    )


def test_confirm_all_makes_valid_high_confidence_command_confirm():
    decision = decide_policy(make_result(), make_intent(), confirm_all=True)

    assert decision.decision == "confirm"
    assert decision.reasons == ["confirm_all_enabled"]


def test_risky_intent_requires_confirmation_when_confirm_all_is_off():
    decision = decide_policy(
        make_result(intent="set_robot_speed"),
        make_intent(name="set_robot_speed", is_risky=True),
        confirm_all=False,
    )

    assert decision.decision == "confirm"
    assert decision.reasons == ["risky_intent_requires_confirmation"]


def test_medium_confidence_requires_confirmation():
    decision = decide_policy(
        make_result(confidence="medium", confidence_score=0.64),
        make_intent(),
        confirm_all=False,
    )

    assert decision.decision == "confirm"
    assert decision.reasons == ["medium_confidence_requires_confirmation"]


def test_low_confidence_is_rejected():
    decision = decide_policy(
        make_result(confidence="low", confidence_score=0.31),
        make_intent(),
    )

    assert decision.decision == "reject"
    assert decision.reasons == ["low_confidence"]


def test_validation_errors_are_rejected_with_readable_reason():
    decision = decide_policy(
        make_result(errors=["missing required slot: value"]),
        make_intent(),
    )

    assert decision.decision == "reject"
    assert decision.reasons == ["validation_failed: missing required slot: value"]


def test_unknown_intent_is_rejected():
    decision = decide_policy(make_result(intent="unknown"), None)

    assert decision.decision == "reject"
    assert decision.reasons == ["unknown_intent"]


def test_intent_mismatch_is_rejected():
    decision = decide_policy(make_result(intent="set_camera_gain"), make_intent())

    assert decision.decision == "reject"
    assert decision.reasons == ["intent_mismatch: set_camera_gain != set_light_intensity"]


def test_safe_high_confidence_command_can_execute_when_confirm_all_is_off():
    decision = decide_policy(make_result(), make_intent(), confirm_all=False)

    assert decision.decision == "execute"
    assert decision.reasons == ["execution_allowed"]


def test_emergency_stop_does_not_bypass_policy_confirmation():
    decision = decide_policy(
        make_result(intent="emergency_stop"),
        make_intent(name="emergency_stop", is_risky=True),
        confirm_all=False,
    )

    assert decision.decision == "confirm"
    assert decision.reasons == ["risky_intent_requires_confirmation"]


def test_disallowed_confirmation_falls_back_to_reject():
    decision = decide_policy(
        make_result(confidence="medium", confidence_score=0.62),
        make_intent(allowed_decisions=["reject", "execute"]),
        confirm_all=False,
    )

    assert decision.decision == "reject"
    assert decision.reasons == [
        "medium_confidence_requires_confirmation",
        "decision_not_allowed: confirm",
    ]
