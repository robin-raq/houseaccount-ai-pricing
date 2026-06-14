"""FastAPI model service — the internal /predict endpoint the Rails API calls."""

from __future__ import annotations

from fastapi import FastAPI

from pricing.estimator import estimate
from pricing.loader import load_model
from pricing.schemas import PredictRequest, PredictResponse

app = FastAPI(title="HouseAccount Pricing Model Service", version="1.0.0")
_model = load_model()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": _model.model_version}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    return estimate(request, _model)
