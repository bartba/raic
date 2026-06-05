from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_intents_yaml_parses():
    data = load_yaml(ROOT_DIR / "data" / "intents.yaml")
    capabilities = [intent["required_capability"] for intent in data["intents"]]

    assert data["version"] == "1.0"
    assert len(data["intents"]) == 18
    assert data["intents"][0]["name"] == "start_machine"
    assert all(capabilities)


def test_devices_yaml_parses():
    data = load_yaml(ROOT_DIR / "data" / "devices.yaml")
    device_ids = [device["id"] for device in data["devices"]]

    assert data["version"] == "1.0"
    assert len(data["devices"]) == 1
    assert len(device_ids) == len(set(device_ids))
    assert all(device["aliases"] for device in data["devices"])
    assert all(device["components"] for device in data["devices"])


def test_phase1_golden_yaml_parses():
    data = load_yaml(ROOT_DIR / "data" / "golden" / "phase1_golden.yaml")
    intents = load_yaml(ROOT_DIR / "data" / "intents.yaml")
    intent_names = {intent["name"] for intent in intents["intents"]}
    ood_cases = [case for case in data["cases"] if case["expected_intent"] == "unknown"]
    in_domain_cases = [
        case for case in data["cases"] if case["expected_intent"] != "unknown"
    ]

    assert data["version"] == "1.0"
    assert len(data["cases"]) == 38
    assert len(ood_cases) == 2
    assert all(case["expected_intent"] in intent_names for case in in_domain_cases)
