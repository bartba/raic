import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List

from models.request import ClassifyRequest
from models.response import ClassifyResponse
from models.schema import Candidate, PolicyDecision, ValidatedResult
from services.normalizer import (
    find_component_candidates,
    find_device_candidates,
    find_line_ids,
)
from services.prompt_builder import (
    build_candidate_block,
    build_device_block,
    build_system_prompt,
)
from services.result_validator import validate_llm_result
from services.schema_manager import SchemaManager


NormalizeFn = Callable[[str], str]
ClassifyFn = Callable[[str], ValidatedResult]
PolicyFn = Callable[[ValidatedResult], PolicyDecision]


@dataclass(frozen=True)
class PipelineDependencies:
    normalize: NormalizeFn
    classify_normalized: ClassifyFn
    decide_policy: PolicyFn


class ClassificationPipeline:
    def __init__(self, dependencies: PipelineDependencies):
        self.dependencies = dependencies

    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        started_at = time.monotonic()

        normalized_utterance = self.dependencies.normalize(request.utterance)
        validated_result = self.dependencies.classify_normalized(normalized_utterance)
        policy_decision = self.dependencies.decide_policy(validated_result)

        return ClassifyResponse(
            session_id=request.session_id,
            decision=policy_decision.decision,
            intent=validated_result.intent,
            slots=validated_result.slots,
            confidence=validated_result.confidence,
            confidence_score=validated_result.confidence_score,
            is_risky=validated_result.is_risky,
            policy_reasons=policy_decision.reasons,
            processing_time_ms=_elapsed_ms(started_at),
        )


def build_classify_normalized(
    schema_manager: SchemaManager,
    embedder_client: Any,
    vector_store: Any,
    llm_client: Any,
    top_k: int,
    confidence_high: float = 0.85,
    confidence_low: float = 0.60,
) -> ClassifyFn:
    def classify_normalized(normalized_utterance: str) -> ValidatedResult:
        device_candidates = find_device_candidates(normalized_utterance, schema_manager)
        line_ids = find_line_ids(normalized_utterance, schema_manager)
        if not line_ids:
            return _invalid_pipeline_result("missing required slot: line_id")
        if not device_candidates:
            return _invalid_pipeline_result("missing required slot: machine_id")

        component_candidates_by_device = {
            device.id: find_component_candidates(normalized_utterance, device)
            for device in device_candidates
        }

        try:
            query_embedding = embedder_client.embed_text(normalized_utterance)
            search_results = vector_store.search(query_embedding, top_k)
        except Exception as error:
            return _invalid_pipeline_result(str(error))

        candidates = _candidates_from_search_results(search_results)

        system_prompt = build_system_prompt()
        user_prompt = _build_user_prompt(
            normalized_utterance=normalized_utterance,
            candidates=candidates,
            schema_manager=schema_manager,
            device_candidates=device_candidates,
            component_candidates_by_device=component_candidates_by_device,
        )
        try:
            raw_llm_result = llm_client.generate_json(system_prompt, user_prompt)
        except Exception as error:
            return _invalid_pipeline_result(str(error))

        return validate_llm_result(
            raw_llm_result,
            schema_manager,
            confidence_high=confidence_high,
            confidence_low=confidence_low,
            allowed_machine_ids=[device.id for device in device_candidates],
            allowed_line_ids=line_ids,
        )

    return classify_normalized


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def _invalid_pipeline_result(error: str) -> ValidatedResult:
    return ValidatedResult(
        intent="unknown",
        slots={},
        confidence="low",
        confidence_score=0.0,
        is_valid=False,
        errors=[error],
    )


def _candidates_from_search_results(search_results: Iterable[Any]) -> List[Candidate]:
    candidates = []
    for result in search_results:
        metadata = result.metadata
        candidates.append(
            Candidate(
                intent=metadata["intent"],
                score=result.score,
                seed_utterance=metadata["seed_utterance"],
            )
        )
    return candidates


def _build_user_prompt(
    normalized_utterance: str,
    candidates: List[Candidate],
    schema_manager: SchemaManager,
    device_candidates: Iterable[Any],
    component_candidates_by_device: Dict[str, Iterable[Any]],
) -> str:
    return "\n\n".join(
        [
            "Utterance:\n{0}".format(normalized_utterance),
            build_candidate_block(candidates, schema_manager),
            build_device_block(device_candidates, component_candidates_by_device),
        ]
    )
