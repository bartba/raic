from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from models.common import Confidence, Decision


class ClassifyResponse(BaseModel):
    session_id: str
    decision: Decision
    intent: str
    slots: Dict[str, Any] = Field(default_factory=dict)
    confidence: Confidence
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_risky: bool
    policy_reasons: List[str] = Field(default_factory=list)
    processing_time_ms: int = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")
