"""The residual pricing model and conformal interval calibration.

The target is the *correction* to the prior: ``log(final_price) - log(original_estimate)``.
A gradient-boosted regressor learns it from scope/zip/subtype/seasonality, so the
correction is near zero where the prior is already good and meaningful where it isn't.
Intervals come from split-conformal nonconformity in log space (multiplicative band).
"""

from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import CATEGORICAL, align_categoricals, build_features, learn_categories

DEFAULT_PARAMS: dict = {
    "n_estimators": 400,
    "learning_rate": 0.03,
    "num_leaves": 15,
    "min_child_samples": 8,
    "subsample": 0.85,
    "subsample_freq": 1,
    "colsample_bytree": 0.85,
    "reg_lambda": 1.0,
    "random_state": 42,
    "verbose": -1,
}


@dataclass
class FittedResidualModel:
    booster: lgb.LGBMRegressor
    cat_levels: dict[str, pd.Index]
    shrink: float = 1.0


REL_BAND_FLOOR = 0.15  # floor so a zero-width prior still yields a sane interval


def prior_of(df: pd.DataFrame) -> np.ndarray:
    return df["original_estimate"].clip(lower=1.0).to_numpy()


def relative_band(df: pd.DataFrame) -> np.ndarray:
    """The prior's band width relative to its midpoint — a per-job difficulty signal.

    Normalizing the conformal interval by this makes uncertain jobs (where the previous
    model hedged with a wide band) get wider intervals and lower confidence.
    """
    width = (df["estimate_hi"] - df["estimate_lo"]).clip(lower=0).to_numpy()
    return np.clip(width / prior_of(df), REL_BAND_FLOOR, None)


def fit_residual_model(
    train: pd.DataFrame,
    params: dict | None = None,
    *,
    weight_by_uniqueness: bool = False,
    shrink: float = 1.0,
    scope_map: dict | None = None,
) -> FittedResidualModel:
    features = build_features(train, scope_map)
    levels = learn_categories(features)
    target = np.log(train["final_price"].to_numpy()) - np.log(prior_of(train))
    booster = lgb.LGBMRegressor(**(params or DEFAULT_PARAMS))
    weight = 1.0 / train["desc_freq"].to_numpy() if weight_by_uniqueness else None
    booster.fit(
        align_categoricals(features, levels), target,
        categorical_feature=CATEGORICAL, sample_weight=weight,
    )
    return FittedResidualModel(booster, levels, shrink)


def predict_prices(
    fitted: FittedResidualModel, frame: pd.DataFrame, scope_map: dict | None = None
) -> np.ndarray:
    features = align_categoricals(build_features(frame, scope_map), fitted.cat_levels)
    residual = fitted.booster.predict(features)
    return prior_of(frame) * np.exp(fitted.shrink * residual)


def conformal_quantile(oof_pred: np.ndarray, actual: np.ndarray, coverage: float = 0.80) -> float:
    """Log-space nonconformity quantile -> half-width of the multiplicative interval."""
    nonconformity = np.abs(np.log(actual) - np.log(np.clip(oof_pred, 1.0, None)))
    return float(np.quantile(nonconformity, coverage))


def interval_from(point: float, q: float) -> tuple[float, float]:
    return point * float(np.exp(-q)), point * float(np.exp(q))
