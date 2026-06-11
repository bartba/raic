from pathlib import Path

from services.normalizer import (
    find_component_ids,
    find_device_candidates,
    find_device_ids,
    find_line_ids,
    normalize_match_text,
    normalize_text,
)
from services.schema_manager import load_schema


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_real_schema():
    return load_schema(
        str(ROOT_DIR / "data" / "intents.yaml"),
        str(ROOT_DIR / "data" / "devices.yaml"),
    )


def test_normalize_text_collapses_spaces_and_lowercases():
    text = "  Camera   EXPOSURE   1200  "

    assert normalize_text(text) == "camera exposure 1200"


def test_normalize_text_normalizes_units_and_simple_numbers():
    text = "삼번 로봇 속도 30 퍼센트로 알피엠 확인"

    assert normalize_text(text) == "3번 로봇 속도 30 percent로 rpm 확인"


def test_normalize_match_text_removes_spaces_for_alias_matching():
    text = "  포장   검사기  "

    assert normalize_match_text(text) == "포장검사기"


def test_find_device_candidates_matches_real_aliases():
    schema_manager = load_real_schema()
    candidates = find_device_candidates("혼류 포장 검사기 상태 확인", schema_manager)

    assert [device.id for device in candidates] == ["machine_inspection"]


def test_find_device_candidates_matches_machine_alias_without_line_text():
    schema_manager = load_real_schema()
    candidates = find_device_candidates("검사기 상태 확인", schema_manager)

    assert [device.id for device in candidates] == ["machine_inspection"]


def test_find_device_candidates_matches_spacing_variants():
    schema_manager = load_real_schema()
    candidates = find_device_candidates("포장검사기 상태 확인", schema_manager)

    assert [device.id for device in candidates] == ["machine_inspection"]


def test_find_device_ids_requires_device_alias_not_component_only():
    schema_manager = load_real_schema()

    assert find_device_ids("카메라 노출값 800으로 바꿔", schema_manager) == []


def test_find_device_ids_matches_device_alias_with_component_text():
    schema_manager = load_real_schema()
    device_ids = find_device_ids(
        "포장 검사기 카메라 노출값 800으로 바꿔",
        schema_manager,
    )

    assert device_ids == ["machine_inspection"]


def test_find_line_ids_matches_line_id():
    schema_manager = load_real_schema()

    assert find_line_ids("line_packaging 포장 검사기 상태 확인", schema_manager) == [
        "line_packaging"
    ]


def test_find_line_ids_matches_line_alias():
    schema_manager = load_real_schema()

    assert find_line_ids("포장 검사기 상태 확인", schema_manager) == [
        "line_packaging"
    ]


def test_target_candidates_match_natural_line_machine_component_phrase():
    schema_manager = load_real_schema()
    device = schema_manager.get_device("machine_inspection")
    text = "포장 검사기 조명 100 으로 맞춰"

    assert find_line_ids(text, schema_manager) == ["line_packaging"]
    assert find_device_ids(text, schema_manager) == ["machine_inspection"]
    assert find_component_ids(text, device) == ["led_light"]


def test_target_candidates_match_regardless_of_phrase_order():
    schema_manager = load_real_schema()
    device = schema_manager.get_device("machine_inspection")
    texts = [
        "포장 검사기 로봇 속도 50으로 줄여",
        "로봇 속도 50으로 포장 검사기 줄여",
        "속도 50으로 줄여 포장 검사기 로봇",
        "검사기 로봇 속도 50으로 포장 라인 줄여",
    ]

    for text in texts:
        assert find_line_ids(text, schema_manager) == ["line_packaging"]
        assert find_device_ids(text, schema_manager) == ["machine_inspection"]
        assert find_component_ids(text, device) == ["robot"]


def test_find_component_ids_matches_spacing_variants():
    schema_manager = load_real_schema()
    device = schema_manager.get_device("machine_inspection")

    assert find_component_ids("포장검사기조명 200으로 맞춰", device) == ["led_light"]


def test_find_component_ids_matches_light_alias():
    schema_manager = load_real_schema()
    device = schema_manager.get_device("machine_inspection")

    assert find_component_ids("포장 검사기 조명 200 으로 맞춰", device) == [
        "led_light"
    ]


def test_find_device_candidates_returns_empty_list_for_unknown_text():
    schema_manager = load_real_schema()

    assert find_device_candidates("오늘 점심 메뉴 알려줘", schema_manager) == []
