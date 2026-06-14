"""FastAPI model service — the internal /predict endpoint the Rails API calls."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from pricing.categories import PRODUCTION_VERTICALS, TRAINED_CATEGORIES
from pricing.estimator import estimate
from pricing.loader import load_model
from pricing.schemas import PredictRequest, PredictResponse

app = FastAPI(title="HouseAccount Pricing Model Service", version="1.0.0")
_model = load_model()
_META_PATH = Path(__file__).resolve().parents[1] / "model" / "model_meta.json"


def _load_meta() -> dict:
    meta = json.loads(_META_PATH.read_text()) if _META_PATH.exists() else {}
    meta["model_version"] = _model.model_version
    meta["production_verticals"] = sorted(PRODUCTION_VERTICALS)
    meta["trained_categories"] = sorted(TRAINED_CATEGORIES)
    return meta


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": _model.model_version}


@app.get("/meta")
def meta() -> dict:
    return _load_meta()


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    return estimate(request, _model)


# Warm the LLM client + TLS/connection pool at boot so the first real request meets
# the <2s SLA. No-ops instantly when no key is configured (e.g. in tests).
def _warm() -> None:
    import contextlib

    from pricing.llm_scope import extract_scope_llm

    with contextlib.suppress(Exception):
        extract_scope_llm("warmup exterior window cleaning", service_category="Cleaning")


_warm()
