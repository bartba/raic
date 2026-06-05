from pathlib import Path

import pytest

from services.schema_manager import SchemaError, SchemaManager, load_schema


ROOT_DIR = Path(__file__).resolve().parents[2]


def write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_schema_manager_loads_real_files():
    manager = load_schema(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )

    assert manager.is_valid_intent("start_machine")
    assert manager.get_intent("set_robot_speed").is_risky is True
    assert manager.get_intent("set_camera_exposure").required_capability == (
        "camera.exposure.set"
    )
    assert manager.get_intent("set_camera_exposure").target_component_type == "camera"
    assert manager.get_intent("set_light_intensity").target_component_type == "led_light"
    assert manager.get_intent("emergency_stop").required_capability == (
        "machine.emergency_stop"
    )
    assert manager.get_intent("plc_reset").required_capability == "plc.reset"
    assert manager.get_intent("plc_send_out").target_component_type == "plc"
    assert manager.get_intent("check_status").target_scope == "equipment"
    assert len(manager.devices) == 1
    assert manager.get_device("machine_inspection").components[0].id == "camera"
    assert manager.get_device("machine_inspection").components[1].id == "led_light"
    assert all(device.aliases for device in manager.devices)
    assert all(manager.get_device(device.id) is not None for device in manager.devices)
    assert len(manager.list_seed_examples()) == 65


def test_schema_manager_rejects_duplicate_intent_name(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents:
  - name: start_machine
    description: "start"
    target_scope: equipment
    required_capability: machine.start
    is_risky: false
    allowed_decisions: ["confirm"]
    slots: []
    seed_utterances: []
  - name: start_machine
    description: "start again"
    target_scope: equipment
    required_capability: machine.start
    is_risky: false
    allowed_decisions: ["confirm"]
    slots: []
    seed_utterances: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices:
  - id: test_machine
    type: test_machine
    line: line_a
    aliases: ["테스트 장비"]
    capabilities: ["machine.unit.set"]
    components: []
""",
    )

    with pytest.raises(SchemaError, match="duplicate intent name"):
        load_schema(str(intent_path), str(device_path))


def test_schema_manager_rejects_duplicate_device_id(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices:
  - id: conveyor_3
    type: conveyor
    line: line_a
    aliases: []
  - id: conveyor_3
    type: conveyor
    line: line_b
    aliases: []
""",
    )

    with pytest.raises(SchemaError, match="duplicate device id"):
        load_schema(str(intent_path), str(device_path))


def test_schema_manager_rejects_invalid_slot_type(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents:
  - name: set_speed
    description: "speed"
    target_scope: equipment
    required_capability: machine.speed.set
    is_risky: false
    allowed_decisions: ["confirm"]
    slots:
      - name: value
        type: bad_type
        required: true
    seed_utterances: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices: []
""",
    )

    with pytest.raises(SchemaError, match="invalid intent schema"):
        load_schema(str(intent_path), str(device_path))


def test_schema_manager_rejects_enum_slot_without_values(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents:
  - name: set_unit
    description: "unit"
    target_scope: equipment
    required_capability: machine.unit.set
    is_risky: false
    allowed_decisions: ["confirm"]
    slots:
      - name: unit
        type: enum
        required: true
    seed_utterances: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices:
  - id: test_machine
    type: test_machine
    line: line_a
    aliases: ["테스트 장비"]
    capabilities: ["machine.unit.set"]
    components: []
""",
    )

    with pytest.raises(SchemaError, match="enum slot must define values"):
        load_schema(str(intent_path), str(device_path))


def test_schema_manager_classmethod_keeps_working():
    manager = SchemaManager.load(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )

    assert manager.get_intent("check_status") is not None


def test_schema_manager_rejects_unknown_required_capability(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents:
  - name: start_machine
    description: "start"
    target_scope: equipment
    required_capability: machine.unknown
    is_risky: false
    allowed_decisions: ["confirm"]
    slots: []
    seed_utterances: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices:
  - id: machine_inspection
    type: vision_inspection
    line: line_a
    aliases: ["검사기"]
    capabilities: ["machine.start"]
    components: []
""",
    )

    with pytest.raises(SchemaError, match="intent references unknown capability"):
        load_schema(str(intent_path), str(device_path))


def test_schema_manager_rejects_component_intent_without_component_type(tmp_path):
    intent_path = tmp_path / "intents.yaml"
    device_path = tmp_path / "devices.yaml"
    write_yaml(
        intent_path,
        """
version: "1.0"
intents:
  - name: set_camera_gain
    description: "gain"
    target_scope: component
    required_capability: camera.gain.set
    is_risky: false
    allowed_decisions: ["confirm"]
    slots: []
    seed_utterances: []
""",
    )
    write_yaml(
        device_path,
        """
version: "1.0"
devices:
  - id: machine_inspection
    type: vision_inspection
    line: line_a
    aliases: ["검사기"]
    capabilities: []
    components:
      - id: camera
        type: camera
        aliases: ["카메라"]
        capabilities: ["camera.gain.set"]
""",
    )

    with pytest.raises(SchemaError, match="component intent must define"):
        load_schema(str(intent_path), str(device_path))
