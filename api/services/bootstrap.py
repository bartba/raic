from dataclasses import dataclass
from typing import Any

from config import Settings
from services.embedder_client import EmbedderClient
from services.llm_client import LLMClient
from services.normalizer import normalize_text
from services.pipeline import (
    ClassificationPipeline,
    PipelineDependencies,
    build_classify_normalized,
)
from services.policy_engine import decide_policy
from services.schema_manager import SchemaManager, load_schema
from services.vector_store import VectorStore


class BootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeComponents:
    settings: Settings
    schema_manager: SchemaManager
    vector_store: VectorStore
    embedder_client: Any
    llm_client: Any
    pipeline: ClassificationPipeline


def build_runtime_components(
    settings: Settings,
    schema_manager: SchemaManager = None,
    vector_store: VectorStore = None,
    embedder_client: Any = None,
    llm_client: Any = None,
) -> RuntimeComponents:
    _validate_runtime_settings(settings)

    schema_manager = schema_manager or load_schema(
        settings.intent_schema_path,
        settings.device_schema_path,
    )
    vector_store = vector_store or VectorStore.load(
        settings.vector_index_path,
        use_faiss=settings.vector_index_use_faiss,
    )
    embedder_client = embedder_client or EmbedderClient(
        settings.embedder_url,
        timeout_ms=settings.embedder_timeout_ms,
    )
    llm_client = llm_client or LLMClient(
        base_url=settings.llm_api_url,
        model_name=settings.llm_model_name,
        api_key=settings.llm_api_key or None,
        timeout_ms=settings.llm_timeout_ms,
        max_retries=settings.llm_max_retries,
    )

    classify_normalized = build_classify_normalized(
        schema_manager=schema_manager,
        embedder_client=embedder_client,
        vector_store=vector_store,
        llm_client=llm_client,
        top_k=settings.faiss_top_k,
        confidence_high=settings.confidence_high,
        confidence_low=settings.confidence_low,
    )
    pipeline = ClassificationPipeline(
        PipelineDependencies(
            normalize=normalize_text,
            classify_normalized=classify_normalized,
            decide_policy=lambda result: decide_policy(
                result,
                schema_manager.get_intent(result.intent),
                confirm_all=_confirm_all_from_policy_mode(settings.policy_mode),
            ),
        )
    )

    return RuntimeComponents(
        settings=settings,
        schema_manager=schema_manager,
        vector_store=vector_store,
        embedder_client=embedder_client,
        llm_client=llm_client,
        pipeline=pipeline,
    )


def _validate_runtime_settings(settings: Settings) -> None:
    if settings.faiss_top_k <= 0:
        raise BootstrapError("FAISS_TOP_K must be greater than 0")

    if not 0.0 <= settings.confidence_low <= settings.confidence_high <= 1.0:
        raise BootstrapError(
            "confidence thresholds must satisfy 0 <= low <= high <= 1"
        )

    _confirm_all_from_policy_mode(settings.policy_mode)


def _confirm_all_from_policy_mode(policy_mode: str) -> bool:
    if policy_mode == "confirm_all":
        return True
    if policy_mode == "allow_execute":
        return False
    raise BootstrapError("unsupported POLICY_MODE: {0}".format(policy_mode))
