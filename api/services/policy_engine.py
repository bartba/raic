from typing import List, Optional

from models.common import Decision
from models.schema import IntentDef, PolicyDecision, ValidatedResult


def decide_policy(
    result: ValidatedResult,
    intent: Optional[IntentDef],
    confirm_all: bool = True,
) -> PolicyDecision:
    if intent is None or result.intent == "unknown":
        return PolicyDecision(decision="reject", reasons=["unknown_intent"])

    if result.intent != intent.name:
        return PolicyDecision(
            decision="reject",
            reasons=["intent_mismatch: {0} != {1}".format(result.intent, intent.name)],
        )

    if not result.is_valid or result.errors:
        return PolicyDecision(
            decision="reject",
            reasons=["validation_failed: {0}".format("; ".join(result.errors))],
        )

    if result.confidence == "low":
        return PolicyDecision(decision="reject", reasons=["low_confidence"])

    if result.confidence == "medium":
        return _allowed_decision(
            "confirm",
            intent,
            ["medium_confidence_requires_confirmation"],
        )

    if confirm_all:
        return _allowed_decision(
            "confirm",
            intent,
            ["confirm_all_enabled"],
        )

    if result.is_risky or intent.is_risky:
        return _allowed_decision(
            "confirm",
            intent,
            ["risky_intent_requires_confirmation"],
        )

    return _allowed_decision("execute", intent, ["execution_allowed"])


def _allowed_decision(
    decision: Decision,
    intent: IntentDef,
    reasons: List[str],
) -> PolicyDecision:
    if decision in intent.allowed_decisions:
        return PolicyDecision(decision=decision, reasons=reasons)

    if "reject" in intent.allowed_decisions:
        return PolicyDecision(
            decision="reject",
            reasons=reasons + ["decision_not_allowed: {0}".format(decision)],
        )

    return PolicyDecision(
        decision="reject",
        reasons=reasons + ["no_safe_allowed_decision"],
    )
