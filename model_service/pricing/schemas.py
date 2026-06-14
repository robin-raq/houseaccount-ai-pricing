"""Internal predict contract between the Rails API layer and the model service.

This is *not* the external Appendix A shape (Rails owns that). It is the internal
JSON the Rails adapter sends to the Python model service and gets back.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    job_id: str
    service_category: str
    zip_code: str
    job_description: str = Field(max_length=4000)
    service_subtype: str | None = None
    deadline: str | None = None
    booking_month: str | None = None
    job_status: str | None = None
    original_estimate: float | None = None
    original_estimate_lo: float | None = None
    original_estimate_hi: float | None = None


class PredictResponse(BaseModel):
    job_id: str
    estimate_lo: float
    estimate_hi: float
    estimate_midpoint: float
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    scope: dict[str, str] = Field(default_factory=dict)
    ood_reasons: list[str] = Field(default_factory=list)
    latency_ms: int = 0
