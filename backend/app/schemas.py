from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelVariant(str, Enum):
    baseline_gpt = "baseline_gpt"
    prompted_gpt = "prompted_gpt"
    rag_gpt = "rag_gpt"
    finetuned_oss = "finetuned_oss"


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    model_variant: ModelVariant = ModelVariant.baseline_gpt
    model_name: str | None = None


class AskResponse(BaseModel):
    model_variant: ModelVariant
    answer: str
    metadata: dict[str, Any] = Field(default_factory=dict)
