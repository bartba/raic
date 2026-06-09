from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_api_url: str = Field(..., alias="LLM_API_URL")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    api_auth_token: Optional[str] = Field(default=None, alias="API_AUTH_TOKEN")

    llm_model_name: str = Field("Qwen3.5-35B-A3B", alias="LLM_MODEL_NAME")
    llm_timeout_ms: int = Field(800, alias="LLM_TIMEOUT_MS")
    llm_max_retries: int = Field(0, alias="LLM_MAX_RETRIES")
    embedder_url: str = Field("http://embedder:80", alias="EMBEDDER_URL")
    embedder_timeout_ms: int = Field(800, alias="EMBEDDER_TIMEOUT_MS")
    faiss_top_k: int = Field(10, alias="FAISS_TOP_K")
    confidence_high: float = Field(0.85, alias="CONFIDENCE_HIGH")
    confidence_low: float = Field(0.60, alias="CONFIDENCE_LOW")
    policy_mode: str = Field("confirm_all", alias="POLICY_MODE")
    intent_schema_path: str = Field("/app/data/intents.yaml", alias="INTENT_SCHEMA_PATH")
    device_schema_path: str = Field("/app/data/devices.yaml", alias="DEVICE_SCHEMA_PATH")
    vector_index_path: str = Field("/app/data/seed_index.npz", alias="VECTOR_INDEX_PATH")
    vector_index_use_faiss: bool = Field(True, alias="VECTOR_INDEX_USE_FAISS")
    raw_utterance_logging: bool = Field(False, alias="RAW_UTTERANCE_LOGGING")

    model_config = SettingsConfigDict(extra="ignore")
