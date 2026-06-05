from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import Confidence, Decision, SlotType, TargetScope


class SlotDef(BaseModel):
    name: str
    type: SlotType
    required: bool = True
    values: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    default: Optional[Any] = None

    model_config = ConfigDict(extra="forbid")


class IntentDef(BaseModel):
    name: str
    description: str
    is_risky: bool
    slots: List[SlotDef] = Field(default_factory=list)
    target_scope: TargetScope
    required_capability: str
    target_component_type: Optional[str] = None
    allowed_decisions: List[Decision]
    seed_utterances: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ComponentDef(BaseModel):
    id: str
    type: str
    aliases: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DeviceDef(BaseModel):
    id: str
    type: str
    line: str
    aliases: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    components: List[ComponentDef] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class Candidate(BaseModel):
    intent: str
    score: float = Field(..., ge=0.0, le=1.0)
    seed_utterance: str

    model_config = ConfigDict(extra="forbid")


class ValidatedResult(BaseModel):
    intent: str
    slots: Dict[str, Any] = Field(default_factory=dict)
    confidence: Confidence
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_risky: bool = False
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PolicyDecision(BaseModel):
    decision: Decision
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
