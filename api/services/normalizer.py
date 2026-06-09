import re
from typing import List

from models.schema import ComponentDef, DeviceDef
from services.schema_manager import SchemaManager


SPACE_PATTERN = re.compile(r"\s+")

TEXT_REPLACEMENTS = {
    "일번": "1번",
    "이번": "2번",
    "삼번": "3번",
    "사번": "4번",
    "오번": "5번",
    "육번": "6번",
    "칠번": "7번",
    "팔번": "8번",
    "구번": "9번",
    "영번": "0번",
    "알피엠": "rpm",
    "알피 엠": "rpm",
    "퍼센트": "percent",
    "프로": "percent",
}


def normalize_text(text: str) -> str:
    normalized = SPACE_PATTERN.sub(" ", text.strip())
    normalized = normalized.lower()

    for source, target in TEXT_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)

    return normalized


def normalize_match_text(text: str) -> str:
    return normalize_text(text).replace(" ", "")


def find_device_candidates(text: str, schema_manager: SchemaManager) -> List[DeviceDef]:
    normalized_text = normalize_text(text)
    match_text = normalize_match_text(text)
    candidates = []

    for device in schema_manager.devices:
        if _matches_device(normalized_text, match_text, device):
            candidates.append(device)

    return candidates


def find_device_ids(text: str, schema_manager: SchemaManager) -> List[str]:
    return [device.id for device in find_device_candidates(text, schema_manager)]


def find_component_candidates(text: str, device: DeviceDef) -> List[ComponentDef]:
    normalized_text = normalize_text(text)
    match_text = normalize_match_text(text)
    candidates = []

    for component in device.components:
        if _matches_component(normalized_text, match_text, component):
            candidates.append(component)

    return candidates


def find_component_ids(text: str, device: DeviceDef) -> List[str]:
    return [component.id for component in find_component_candidates(text, device)]


def _matches_device(normalized_text: str, match_text: str, device: DeviceDef) -> bool:
    for alias in device.aliases:
        if _matches_alias(normalized_text, match_text, alias):
            return True

    return False


def _matches_component(
    normalized_text: str,
    match_text: str,
    component: ComponentDef,
) -> bool:
    for alias in component.aliases:
        if _matches_alias(normalized_text, match_text, alias):
            return True
    return False


def _matches_alias(normalized_text: str, match_text: str, alias: str) -> bool:
    normalized_alias = normalize_text(alias)
    return (
        normalized_alias in normalized_text
        or normalized_alias.replace(" ", "") in match_text
    )
