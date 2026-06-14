"""Orchestration: booking request -> scope -> model -> intervals -> confidence.

The pricing model is injected behind the ``PricingModel`` protocol, so the same
orchestration runs against a trained model in production and a ``StubModel`` in tests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from . import confidence as confidence_scoring
from .llm_scope import extract_scope_llm
from .schemas import PredictRequest, PredictResponse
from .scope import extract_scope_fallback


@dataclass(frozen=True)
class Prediction:
    estimate_lo: float
    estimate_hi: float
    estimate_midpoint: float


@runtime_checkable
class PricingModel(Protocol):
    model_version: str
    median_interval: float

    def predict(self, request: PredictRequest, scope: dict[str, str]) -> Prediction: ...


@dataclass
class StubModel:
    """Deterministic placeholder used before the real model is trained.

    Not a pricing table — a single base value with a fixed relative band, present only
    so the Rails<->Python contract and the calibration path are testable end to end.
    A trained, feature-aware model replaces it once the dataset is available.
    """

    model_version: str = "stub-0"
    median_interval: float = 150.0
    base: float = 250.0

    def predict(self, request: PredictRequest, scope: dict[str, str]) -> Prediction:
        point = float(request.original_estimate or self.base)
        return Prediction(
            estimate_lo=round(point * 0.8, 2),
            estimate_hi=round(point * 1.2, 2),
            estimate_midpoint=round(point, 2),
        )


def extract_scope(request: PredictRequest, *, use_llm: bool = True) -> dict[str, str]:
    """Prefer LLM scope signals; fall back to deterministic parsing."""
    if use_llm:
        llm = extract_scope_llm(
            request.job_description,
            service_category=request.service_category,
            service_subtype=request.service_subtype,
        )
        if llm:
            return llm
    return extract_scope_fallback(request.job_description)


def estimate(
    request: PredictRequest, model: PricingModel, *, use_llm: bool = True
) -> PredictResponse:
    started = time.perf_counter()
    scope = extract_scope(request, use_llm=use_llm)
    prediction = model.predict(request, scope)
    confidence = confidence_scoring.score(
        midpoint=prediction.estimate_midpoint,
        estimate_lo=prediction.estimate_lo,
        estimate_hi=prediction.estimate_hi,
        service_category=request.service_category,
        median_interval=model.median_interval,
    )
    return PredictResponse(
        job_id=request.job_id,
        estimate_lo=prediction.estimate_lo,
        estimate_hi=prediction.estimate_hi,
        estimate_midpoint=prediction.estimate_midpoint,
        confidence=confidence.value,
        model_version=model.model_version,
        scope=scope,
        ood_reasons=list(confidence.ood_reasons),
        latency_ms=round((time.perf_counter() - started) * 1000),
    )
