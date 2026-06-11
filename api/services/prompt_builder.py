from typing import Dict, Iterable, List, Optional

from models.schema import Candidate, ComponentDef, DeviceDef, SlotDef
from services.schema_manager import SchemaManager


def build_system_prompt() -> str:
    return "\n".join(
        [
            "You extract intent and slots from Korean factory voice commands.",
            "Return JSON only. Do not include markdown, comments, or explanations.",
            "Choose intent only from the provided candidate intents.",
            "If no candidate intent matches, return intent as unknown.",
            "Return exactly these top-level fields: intent, slots, confidence_score.",
            "Do not return or decide execute, confirm, reject, policy, or safety decision.",
            "Use slot names and value types exactly as defined in the provided schema.",
            "Use confidence_score as a number from 0 to 1.",
        ]
    )


def build_candidate_block(
    candidates: Iterable[Candidate],
    schema_manager: SchemaManager,
) -> str:
    intent_examples = _collect_candidate_examples(candidates, schema_manager)
    if not intent_examples:
        return "Candidate intents:\n- none"

    lines = ["Candidate intents:"]
    for intent_name, seed_utterances in intent_examples.items():
        intent = schema_manager.get_intent(intent_name)
        if intent is None:
            continue

        lines.append("- intent: {0}".format(intent.name))
        lines.append("  description: {0}".format(intent.description))
        lines.append("  target_scope: {0}".format(intent.target_scope))
        lines.append("  required_capability: {0}".format(intent.required_capability))
        lines.append("  slots:")
        for slot in intent.slots:
            lines.append("    - {0}".format(_format_slot(slot)))
        lines.append("  seed_utterances:")
        for seed_utterance in seed_utterances:
            lines.append("    - {0}".format(seed_utterance))

    return "\n".join(lines)


def build_device_block(
    devices: Iterable[DeviceDef],
    component_candidates_by_device: Optional[Dict[str, Iterable[ComponentDef]]] = None,
) -> str:
    device_list = list(devices)
    if not device_list:
        return "Device candidates:\n- none"

    component_candidates_by_device = component_candidates_by_device or {}
    lines = ["Device candidates:"]
    for device in device_list:
        lines.append("- device_id: {0}".format(device.id))
        lines.append("  line_id: {0}".format(device.line_id))
        lines.append("  line_aliases: {0}".format(device.line_aliases))
        lines.append("  aliases: {0}".format(device.aliases))
        lines.append("  capabilities: {0}".format(device.capabilities))

        component_candidates = list(component_candidates_by_device.get(device.id, []))
        lines.append("  component_candidates:")
        if not component_candidates:
            lines.append("    - none")
            continue

        for component in component_candidates:
            lines.append("    - component_id: {0}".format(component.id))
            lines.append("      aliases: {0}".format(component.aliases))
            lines.append("      capabilities: {0}".format(component.capabilities))

    return "\n".join(lines)


def _collect_candidate_examples(
    candidates: Iterable[Candidate],
    schema_manager: SchemaManager,
) -> Dict[str, List[str]]:
    intent_examples: Dict[str, List[str]] = {}

    for candidate in candidates:
        intent = schema_manager.get_intent(candidate.intent)
        if intent is None:
            continue

        examples = intent_examples.setdefault(intent.name, [])
        if candidate.seed_utterance not in examples:
            examples.append(candidate.seed_utterance)

    return intent_examples


def _format_slot(slot: SlotDef) -> str:
    parts = [
        "name={0}".format(slot.name),
        "type={0}".format(slot.type),
        "required={0}".format(str(slot.required).lower()),
    ]

    if slot.values is not None:
        parts.append("values={0}".format(slot.values))
    if slot.min is not None:
        parts.append("min={0}".format(slot.min))
    if slot.max is not None:
        parts.append("max={0}".format(slot.max))
    if slot.default is not None:
        parts.append("default={0}".format(slot.default))

    return ", ".join(parts)
