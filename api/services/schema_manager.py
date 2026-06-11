from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Type

import yaml
from pydantic import BaseModel
from pydantic import ValidationError

from models.schema import ComponentDef, DeviceDef, IntentDef, SlotDef


class SchemaError(ValueError):
    pass


class SchemaManager:
    def __init__(self, intents: List[IntentDef], devices: List[DeviceDef]):
        self.intents = intents
        self.devices = devices
        self._intent_by_name = {intent.name: intent for intent in intents}
        self._device_by_id = {device.id: device for device in devices}

    @classmethod
    def load(cls, intent_path: str, device_path: str) -> "SchemaManager":
        return load_schema(intent_path, device_path)

    def get_intent(self, name: str) -> Optional[IntentDef]:
        return self._intent_by_name.get(name)

    def is_valid_intent(self, name: str) -> bool:
        return name in self._intent_by_name

    def get_device(self, device_id: str) -> Optional[DeviceDef]:
        return self._device_by_id.get(device_id)

    def list_seed_examples(self) -> List[str]:
        examples = []
        for intent in self.intents:
            examples.extend(intent.seed_utterances)
        return examples

    def list_seed_records(self) -> List[Dict[str, Any]]:
        records = []
        for intent in self.intents:
            for seed_utterance in intent.seed_utterances:
                records.append(
                    {
                        "intent": intent.name,
                        "seed_utterance": seed_utterance,
                        "is_risky": intent.is_risky,
                        "target_scope": intent.target_scope,
                        "required_capability": intent.required_capability,
                    }
                )
        return records


def load_schema(intent_path: str, device_path: str) -> SchemaManager:
    intents = _load_model_list(intent_path, "intents", IntentDef, "intent")
    devices = _load_model_list(device_path, "devices", DeviceDef, "device")

    _require_unique([intent.name for intent in intents], "intent name")
    _require_unique([device.id for device in devices], "device id")
    valid_capabilities = _collect_capabilities(devices)

    for device in devices:
        _validate_device(device)

    for intent in intents:
        _validate_intent(intent, valid_capabilities)

    return SchemaManager(intents=intents, devices=devices)


def _load_model_list(
    path: str,
    key: str,
    model_class: Type[BaseModel],
    label: str,
) -> List[Any]:
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except OSError as error:
        raise SchemaError("cannot read schema file: {0}".format(path)) from error

    if not isinstance(data, dict):
        raise SchemaError("schema file must contain a mapping: {0}".format(path))

    items = data.get(key)
    if not isinstance(items, list):
        raise SchemaError("{0} must contain a list field: {1}".format(path, key))

    parsed_items = []
    for item in items:
        try:
            parsed_items.append(model_class.model_validate(item))
        except ValidationError as error:
            raise SchemaError(
                "invalid {0} schema in {1}: {2}".format(label, path, error)
            ) from error

    return parsed_items


def _require_unique(values: Iterable[str], label: str) -> None:
    seen = set()
    for value in values:
        if value in seen:
            raise SchemaError("duplicate {0}: {1}".format(label, value))
        seen.add(value)


def _validate_device(device: DeviceDef) -> None:
    _require_unique(device.capabilities, "device capability")
    _require_unique([component.id for component in device.components], "component id")

    for component in device.components:
        _validate_component(device, component)


def _validate_component(device: DeviceDef, component: ComponentDef) -> None:
    _require_unique(component.capabilities, "component capability")

    if not component.aliases:
        raise SchemaError(
            "component must define aliases: {0}.{1}".format(device.id, component.id)
        )


def _validate_intent(intent: IntentDef, valid_capabilities: Set[str]) -> None:
    _require_unique([slot.name for slot in intent.slots], "slot name")

    if intent.required_capability not in valid_capabilities:
        raise SchemaError(
            "intent references unknown capability: {0}.{1}".format(
                intent.name, intent.required_capability
            )
        )

    _validate_required_slot(intent, "machine_id")
    _validate_required_slot(intent, "line_id")

    if intent.target_scope == "component":
        _validate_component_slot(intent)

    for slot in intent.slots:
        _validate_slot(intent, slot)


def _validate_required_slot(intent: IntentDef, name: str) -> None:
    slot = _find_slot(intent, name)
    if slot is None or not slot.required or slot.type != "string":
        raise SchemaError(
            "intent must define required string slot: {0}.{1}".format(
                intent.name,
                name,
            )
        )


def _validate_component_slot(intent: IntentDef) -> None:
    slot = _find_slot(intent, "component_id")
    if slot is None or slot.type != "string":
        raise SchemaError(
            "component intent must define component_id slot: {0}".format(intent.name)
        )


def _find_slot(intent: IntentDef, name: str) -> Optional[SlotDef]:
    for slot in intent.slots:
        if slot.name == name:
            return slot
    return None


def _collect_capabilities(devices: List[DeviceDef]) -> Set[str]:
    capabilities = set()
    for device in devices:
        capabilities.update(device.capabilities)
        for component in device.components:
            capabilities.update(component.capabilities)
    return capabilities


def _validate_slot(intent: IntentDef, slot: SlotDef) -> None:
    if slot.type == "enum" and not slot.values:
        raise SchemaError(
            "enum slot must define values: {0}.{1}".format(intent.name, slot.name)
        )

    if slot.min is not None and slot.max is not None and slot.min > slot.max:
        raise SchemaError(
            "slot min cannot be greater than max: {0}.{1}".format(
                intent.name, slot.name
            )
        )

    if slot.values is not None and slot.default is not None and slot.default not in slot.values:
        raise SchemaError(
            "slot default must be one of values: {0}.{1}".format(intent.name, slot.name)
        )
