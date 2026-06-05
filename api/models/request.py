from pydantic import BaseModel, ConfigDict, Field


class ClassifyRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    operator_id: str = Field(..., min_length=1)
    utterance: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")
