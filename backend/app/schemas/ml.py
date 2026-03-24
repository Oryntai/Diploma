from __future__ import annotations

from pydantic import BaseModel, Field


class MLStatusResponse(BaseModel):
    model_path: str
    model_exists: bool
    model_format: str
    model_loaded: bool
    ready_for_inference: bool
    detail: str


class MLPredictRequest(BaseModel):
    features: list[float] | dict[str, float | int] = Field()


class MLPredictResponse(BaseModel):
    prediction: float
    model_format: str
    model_path: str
    threshold: float | None = None
    label: str | None = None
    risk_level: str | None = None
