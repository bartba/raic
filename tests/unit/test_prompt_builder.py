from pathlib import Path

from models.schema import Candidate
from services.normalizer import find_component_candidates, find_device_candidates
from services.prompt_builder import (
    build_candidate_block,
    build_device_block,
    build_system_prompt,
)
from services.schema_manager import load_schema


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_real_schema():
    return load_schema(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )


def test_build_system_prompt_limits_llm_role():
    prompt = build_system_prompt()

    assert "Return JSON only" in prompt
    assert "provided candidate intents" in prompt
    assert "intent, slots, confidence_score" in prompt
    assert "Do not return or decide execute, confirm, reject" in prompt


def test_build_system_prompt_does_not_ask_for_policy_decision():
    prompt = build_system_prompt().lower()

    assert "do not return or decide" in prompt
    assert "top-level fields: intent, slots, confidence_score" in prompt


def test_build_candidate_block_handles_empty_candidates():
    block = build_candidate_block([], load_real_schema())

    assert block == "Candidate intents:\n- none"


def test_build_candidate_block_includes_single_intent_schema():
    block = build_candidate_block(
        [
            Candidate(
                intent="set_light_intensity",
                score=0.92,
                seed_utterance="조명 150으로 맞춰",
            )
        ],
        load_real_schema(),
    )

    assert "intent: set_light_intensity" in block
    assert "description: 조명 밝기를 설정한다." in block
    assert "target_scope: component" in block
    assert "required_capability: light.intensity.set" in block
    assert "name=value, type=integer, required=true, min=0.0, max=255.0" in block
    assert "조명 150으로 맞춰" in block


def test_build_candidate_block_includes_multiple_intents():
    block = build_candidate_block(
        [
            Candidate(
                intent="check_status",
                score=0.88,
                seed_utterance="장비 상태 알려줘",
            ),
            Candidate(
                intent="set_camera_exposure",
                score=0.81,
                seed_utterance="카메라 노출값 800으로 바꿔",
            ),
        ],
        load_real_schema(),
    )

    assert "intent: check_status" in block
    assert "intent: set_camera_exposure" in block
    assert "name=component_id, type=string, required=false, default=camera" in block


def test_build_candidate_block_ignores_unknown_candidate_intent():
    block = build_candidate_block(
        [
            Candidate(intent="turn_on_aircon", score=0.7, seed_utterance="에어컨 켜"),
            Candidate(intent="check_status", score=0.65, seed_utterance="상태 확인해"),
        ],
        load_real_schema(),
    )

    assert "turn_on_aircon" not in block
    assert "intent: check_status" in block


def test_build_device_block_handles_empty_candidates():
    block = build_device_block([])

    assert block == "Device candidates:\n- none"


def test_build_device_block_includes_device_candidate_capabilities():
    schema_manager = load_real_schema()
    devices = find_device_candidates("검사기 상태 확인해", schema_manager)

    block = build_device_block(devices)

    assert "device_id: machine_inspection" in block
    assert "type: vision_inspection" in block
    assert "line: line_packaging" in block
    assert "machine.status.read" in block
    assert "component_candidates:\n    - none" in block


def test_build_device_block_includes_component_candidate_capabilities():
    schema_manager = load_real_schema()
    devices = find_device_candidates("카메라 노출값 800으로 바꿔", schema_manager)
    component_candidates_by_device = {
        device.id: find_component_candidates("카메라 노출값 800으로 바꿔", device)
        for device in devices
    }

    block = build_device_block(devices, component_candidates_by_device)

    assert "device_id: machine_inspection" in block
    assert "component_id: camera" in block
    assert "type: camera" in block
    assert "camera.exposure.set" in block
