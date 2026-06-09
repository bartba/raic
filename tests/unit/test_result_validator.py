import json
from pathlib import Path

from services.result_validator import validate_llm_result
from services.schema_manager import load_schema


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_real_schema():
    return load_schema(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )


def test_validate_llm_result_accepts_valid_dict_and_applies_defaults():
    result = validate_llm_result(
        {
            "intent": "set_light_intensity",
            "slots": {"value": 120},
            "confidence_score": 0.91,
        },
        load_real_schema(),
    )

    assert result.is_valid is True
    assert result.intent == "set_light_intensity"
    assert result.confidence == "high"
    assert result.slots == {
        "machine_id": "machine_inspection",
        "component_id": "led_light",
        "value": 120,
    }
    assert result.errors == []


def test_validate_llm_result_accepts_json_string():
    raw_result = json.dumps(
        {
            "intent": "set_camera_exposure",
            "slots": {"machine_id": "machine_inspection", "value": "800"},
            "confidence_score": 0.82,
        }
    )

    result = validate_llm_result(raw_result, load_real_schema())

    assert result.is_valid is True
    assert result.slots["component_id"] == "camera"
    assert result.slots["value"] == 800
    assert result.confidence == "medium"


def test_validate_llm_result_accepts_custom_confidence_thresholds():
    result = validate_llm_result(
        {
            "intent": "check_status",
            "slots": {"machine_id": "machine_inspection"},
            "confidence_score": 0.82,
        },
        load_real_schema(),
        confidence_high=0.80,
        confidence_low=0.50,
    )

    assert result.confidence == "high"


def test_validate_llm_result_rejects_invalid_json():
    result = validate_llm_result("{bad json", load_real_schema())

    assert result.is_valid is False
    assert result.intent == "unknown"
    assert result.errors == ["llm result must be valid json"]


def test_validate_llm_result_rejects_unknown_intent():
    result = validate_llm_result(
        {
            "intent": "open_window",
            "slots": {},
            "confidence_score": 0.9,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert result.intent == "unknown"
    assert result.errors == ["unknown intent: open_window"]


def test_validate_llm_result_rejects_missing_required_slot():
    result = validate_llm_result(
        {
            "intent": "set_light_intensity",
            "slots": {"machine_id": "machine_inspection"},
            "confidence_score": 0.9,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert "missing required slot: value" in result.errors


def test_validate_llm_result_rejects_range_error():
    result = validate_llm_result(
        {
            "intent": "set_light_intensity",
            "slots": {"machine_id": "machine_inspection", "value": 300},
            "confidence_score": 0.9,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert "slot above maximum: value" in result.errors


def test_validate_llm_result_rejects_enum_error():
    result = validate_llm_result(
        {
            "intent": "set_robot_speed",
            "slots": {
                "machine_id": "machine_inspection",
                "component_id": "robot",
                "value": 50,
                "unit": "rpm",
            },
            "confidence_score": 0.88,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert "slot must be one of allowed values: unit" in result.errors


def test_validate_llm_result_rejects_wrong_component_target():
    result = validate_llm_result(
        {
            "intent": "set_camera_exposure",
            "slots": {
                "machine_id": "machine_inspection",
                "component_id": "led_light",
                "value": 800,
            },
            "confidence_score": 0.9,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert "component type mismatch: led_light != camera" in result.errors
    assert "component does not support capability: camera.exposure.set" in result.errors


def test_validate_llm_result_rejects_bad_confidence_score():
    result = validate_llm_result(
        {
            "intent": "check_status",
            "slots": {"machine_id": "machine_inspection"},
            "confidence_score": 1.2,
        },
        load_real_schema(),
    )

    assert result.is_valid is False
    assert "confidence_score must be a number between 0 and 1" in result.errors
