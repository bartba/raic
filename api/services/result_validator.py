import json
from typing import Any, Dict, List, Optional, Tuple

from models.common import Confidence
from models.schema import ComponentDef, DeviceDef, IntentDef, SlotDef, ValidatedResult
from services.schema_manager import SchemaManager


def validate_llm_result(
    raw_result: Any,
    schema_manager: SchemaManager,
    confidence_high: float = 0.85,
    confidence_low: float = 0.60,
    allowed_machine_ids: Optional[List[str]] = None,
    allowed_line_ids: Optional[List[str]] = None,
) -> ValidatedResult:
    data, parse_errors = _parse_result(raw_result)
    if parse_errors:
        return _invalid_result(
            "unknown",
            {},
            0.0,
            parse_errors,
            confidence_high=confidence_high,
            confidence_low=confidence_low,
        )

    intent_name = data.get("intent")
    raw_slots = data.get("slots", {})
    confidence_score, confidence_errors = _parse_confidence_score(
        data.get("confidence_score")
    )

    if not isinstance(intent_name, str) or not intent_name:
        return _invalid_result(
            "unknown",
            {},
            confidence_score,
            ["missing intent"] + confidence_errors,
            confidence_high=confidence_high,
            confidence_low=confidence_low,
        )

    intent = schema_manager.get_intent(intent_name)
    if intent is None:
        return _invalid_result(
            "unknown",
            {},
            confidence_score,
            ["unknown intent: {0}".format(intent_name)] + confidence_errors,
            confidence_high=confidence_high,
            confidence_low=confidence_low,
        )

    if not isinstance(raw_slots, dict):
        return _invalid_result(
            intent.name,
            {},
            confidence_score,
            ["slots must be an object"] + confidence_errors,
            intent.is_risky,
            confidence_high=confidence_high,
            confidence_low=confidence_low,
        )

    slots, slot_errors = _validate_slots(
        raw_slots,
        intent,
        schema_manager,
        allowed_machine_ids=allowed_machine_ids,
        allowed_line_ids=allowed_line_ids,
    )
    errors = confidence_errors + slot_errors

    return ValidatedResult(
        intent=intent.name,
        slots=slots,
        confidence=_confidence_from_score(
            confidence_score,
            confidence_high,
            confidence_low,
        ),
        confidence_score=confidence_score,
        is_risky=intent.is_risky,
        is_valid=not errors,
        errors=errors,
    )


def _parse_result(raw_result: Any) -> Tuple[Dict[str, Any], List[str]]:
    if isinstance(raw_result, str):
        try:
            raw_result = json.loads(raw_result)
        except json.JSONDecodeError:
            return {}, ["llm result must be valid json"]

    if not isinstance(raw_result, dict):
        return {}, ["llm result must be an object"]

    return raw_result, []


def _parse_confidence_score(value: Any) -> Tuple[float, List[str]]:
    if isinstance(value, bool) or value is None:
        return 0.0, ["confidence_score must be a number between 0 and 1"]

    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0, ["confidence_score must be a number between 0 and 1"]

    if score < 0.0 or score > 1.0:
        return 0.0, ["confidence_score must be a number between 0 and 1"]

    return score, []


def _validate_slots(
    raw_slots: Dict[str, Any],
    intent: IntentDef,
    schema_manager: SchemaManager,
    allowed_machine_ids: Optional[List[str]] = None,
    allowed_line_ids: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    slot_defs = {slot.name: slot for slot in intent.slots}
    slots: Dict[str, Any] = {}
    errors: List[str] = []

    for raw_name in raw_slots:
        if raw_name not in slot_defs:
            errors.append("unknown slot: {0}".format(raw_name))

    for slot_def in intent.slots:
        value = raw_slots.get(slot_def.name)
        if value is None:
            if slot_def.default is not None:
                value = slot_def.default
            elif slot_def.required:
                errors.append("missing required slot: {0}".format(slot_def.name))
                continue
            else:
                continue

        parsed_value, value_errors = _validate_slot_value(slot_def, value)
        errors.extend(value_errors)
        if not value_errors:
            slots[slot_def.name] = parsed_value

    errors.extend(
        _validate_target(
            intent,
            slots,
            schema_manager,
            allowed_machine_ids=allowed_machine_ids,
            allowed_line_ids=allowed_line_ids,
        )
    )
    return slots, errors


def _validate_slot_value(slot_def: SlotDef, value: Any) -> Tuple[Any, List[str]]:
    if slot_def.type == "string":
        if not isinstance(value, str) or not value:
            return value, ["slot must be a non-empty string: {0}".format(slot_def.name)]
        return value, []

    if slot_def.type == "boolean":
        if not isinstance(value, bool):
            return value, ["slot must be a boolean: {0}".format(slot_def.name)]
        return value, []

    if slot_def.type == "integer":
        parsed_int = _parse_integer(value)
        if parsed_int is None:
            return value, ["slot must be an integer: {0}".format(slot_def.name)]
        return _validate_range(slot_def, parsed_int)

    if slot_def.type == "number":
        parsed_number = _parse_number(value)
        if parsed_number is None:
            return value, ["slot must be a number: {0}".format(slot_def.name)]
        return _validate_range(slot_def, parsed_number)

    if slot_def.type == "enum":
        if value not in (slot_def.values or []):
            return value, ["slot must be one of allowed values: {0}".format(slot_def.name)]
        return value, []

    return value, ["unsupported slot type: {0}".format(slot_def.name)]


def _parse_integer(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        if parsed.is_integer():
            return int(parsed)

    return None


def _parse_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None

    return None


def _validate_range(slot_def: SlotDef, value: Any) -> Tuple[Any, List[str]]:
    if slot_def.min is not None and value < slot_def.min:
        return value, ["slot below minimum: {0}".format(slot_def.name)]

    if slot_def.max is not None and value > slot_def.max:
        return value, ["slot above maximum: {0}".format(slot_def.name)]

    return value, []


def _validate_target(
    intent: IntentDef,
    slots: Dict[str, Any],
    schema_manager: SchemaManager,
    allowed_machine_ids: Optional[List[str]] = None,
    allowed_line_ids: Optional[List[str]] = None,
) -> List[str]:
    if "machine_id" not in slots or "line_id" not in slots:
        return []

    if (
        allowed_machine_ids is not None
        and slots["machine_id"] not in allowed_machine_ids
    ):
        return ["machine_id not found in utterance: {0}".format(slots["machine_id"])]

    if allowed_line_ids is not None and slots["line_id"] not in allowed_line_ids:
        return ["line_id not found in utterance: {0}".format(slots["line_id"])]

    device = schema_manager.get_device(slots.get("machine_id"))
    if device is None:
        return ["unknown machine_id: {0}".format(slots.get("machine_id"))]

    if slots.get("line_id") != device.line_id:
        return [
            "line_id does not match machine_id: {0} != {1}".format(
                slots.get("line_id"),
                device.line_id,
            )
        ]

    if intent.target_scope == "equipment":
        if intent.required_capability not in device.capabilities:
            return [
                "machine does not support capability: {0}".format(
                    intent.required_capability
                )
            ]
        return []

    component = _find_component(device, slots.get("component_id"))
    if component is None:
        return ["unknown component_id: {0}".format(slots.get("component_id"))]

    errors = []
    if intent.required_capability not in component.capabilities:
        errors.append(
            "component does not support capability: {0}".format(
                intent.required_capability
            )
        )

    return errors


def _find_component(device: DeviceDef, component_id: Any) -> Optional[ComponentDef]:
    if not isinstance(component_id, str):
        return None

    for component in device.components:
        if component.id == component_id:
            return component

    return None


def _confidence_from_score(
    score: float,
    confidence_high: float,
    confidence_low: float,
) -> Confidence:
    if score >= confidence_high:
        return "high"
    if score >= confidence_low:
        return "medium"
    return "low"


def _invalid_result(
    intent: str,
    slots: Dict[str, Any],
    confidence_score: float,
    errors: List[str],
    is_risky: bool = False,
    confidence_high: float = 0.85,
    confidence_low: float = 0.60,
) -> ValidatedResult:
    return ValidatedResult(
        intent=intent,
        slots=slots,
        confidence=_confidence_from_score(
            confidence_score,
            confidence_high,
            confidence_low,
        ),
        confidence_score=confidence_score,
        is_risky=is_risky,
        is_valid=False,
        errors=errors,
    )
