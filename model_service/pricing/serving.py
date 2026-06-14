"""The trained pricing model in serving form (implements the PricingModel protocol).

Turns a single booking request into a point estimate + conformal interval. Handles the
optional ``original_estimate`` prior: when absent, it is imputed from a per-category
median and the interval is widened so the confidence layer reflects the added uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import data
from .categories import canonical_category
from .estimator import Prediction
from .features import align_categoricals, build_features
from .model import FittedResidualModel, interval_from, relative_band
from .schemas import PredictRequest

IMPUTED_PRIOR_WIDENING = 1.5


@dataclass
class TrainedModel:
    fitted: FittedResidualModel
    conformal_q: float
    median_interval: float
    model_version: str
    category_prior: dict[str, float]
    global_prior: float
    use_llm_scope: bool = False

    def predict(self, request: PredictRequest, scope: dict[str, str]) -> Prediction:
        frame, imputed = self._frame(request)
        scope_map = {request.job_description: scope} if self.use_llm_scope else None
        features = align_categoricals(build_features(frame, scope_map), self.fitted.cat_levels)
        residual = float(self.fitted.booster.predict(features)[0])
        prior = float(frame["original_estimate"].iloc[0])
        point = prior * float(np.exp(self.fitted.shrink * residual))
        band = float(relative_band(frame)[0])
        half_width = self.conformal_q * band * (IMPUTED_PRIOR_WIDENING if imputed else 1.0)
        lo, hi = interval_from(point, half_width)
        return Prediction(round(lo, 2), round(hi, 2), round(point, 2))

    def _frame(self, request: PredictRequest) -> tuple[pd.DataFrame, bool]:
        imputed = request.original_estimate is None
        prior = request.original_estimate
        if prior is None:
            canonical = canonical_category(request.service_category)
            prior = self.category_prior.get(canonical, self.global_prior)
        lo = prior * 0.8 if request.original_estimate_lo is None else request.original_estimate_lo
        hi = prior * 1.2 if request.original_estimate_hi is None else request.original_estimate_hi
        raw = pd.DataFrame(
            [
                {
                    "service_category": request.service_category,
                    "service_subtype": request.service_subtype or "",
                    "zip_code": request.zip_code,
                    "booking_month": request.booking_month or "",
                    "job_description": request.job_description,
                    "estimate_lo": lo,
                    "estimate_hi": hi,
                    "original_estimate": prior,
                    "final_price": np.nan,
                    "deadline": request.deadline,
                }
            ]
        )
        return data.clean(raw), imputed
