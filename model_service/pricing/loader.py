"""Load the trained pricing model, or fall back to the stub before training."""

from __future__ import annotations

import logging
import os

from .estimator import PricingModel, StubModel

ARTIFACT_PATH = os.environ.get("PRICING_MODEL_PATH", "artifacts/model.joblib")
_log = logging.getLogger("pricing")


def load_model() -> PricingModel:
    if os.path.exists(ARTIFACT_PATH):
        import joblib

        # Trust boundary: this artifact is first-party — written only by our own
        # `make train` pipeline into our own artifacts/ dir, never accepted from a
        # user or network. joblib/pickle deserialization is safe here for that reason.
        _log.info("loading trained model from %s", ARTIFACT_PATH)
        return joblib.load(ARTIFACT_PATH)
    _log.warning("no model artifact at %s — using StubModel (train to replace)", ARTIFACT_PATH)
    return StubModel()
