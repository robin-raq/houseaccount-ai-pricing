"""MAPE evaluation with grouped cross-validation.

Rows are grouped by ``job_description`` so the augmented templates (which repeat the
same description across ZIPs/months) never sit in both train and test — otherwise the
out-of-fold score would be inflated by leakage. Reports the two bars the brief grades:
blended MAPE on all priced rows and real-only MAPE on the unique-description subset.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

FitPredict = Callable[[pd.DataFrame, pd.DataFrame], np.ndarray]

# The brief states blended 11.6% and real-only ~40%; reproduced from the raw data,
# the actual baseline MAPEs are 11.56% (411 priced) and 35.87% (31 real jobs).
BASELINE_BLENDED = 11.56
BASELINE_REAL = 35.87


def ape(pred: np.ndarray, actual: np.ndarray) -> np.ndarray:
    return np.abs(pred - actual) / np.abs(actual) * 100.0


def mape(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.mean(ape(pred, actual)))


def median_ape(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.median(ape(pred, actual)))


def grouped_oof(df: pd.DataFrame, fit_predict: FitPredict, n_splits: int = 5) -> np.ndarray:
    """Out-of-fold predictions, grouped by description to prevent template leakage."""
    codes = pd.factorize(df["job_description"])[0]
    splitter = GroupKFold(n_splits=n_splits)
    oof = np.full(len(df), np.nan)
    positions = np.arange(len(df))
    for train_idx, test_idx in splitter.split(df, groups=codes):
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        oof[np.isin(positions, test_idx)] = fit_predict(train, test)
    return oof


def evaluate(df_priced: pd.DataFrame, fit_predict: FitPredict, n_splits: int = 5) -> dict:
    oof = grouped_oof(df_priced, fit_predict, n_splits)
    actual = df_priced["final_price"].to_numpy()
    baseline = df_priced["original_estimate"].to_numpy()
    real = df_priced["is_real"].to_numpy()

    blended = mape(oof, actual)
    real_only = mape(oof[real], actual[real])
    return {
        "n": int(len(df_priced)),
        "blended_mape": round(blended, 2),
        "blended_median_ape": round(median_ape(oof, actual), 2),
        "baseline_blended_mape": round(mape(baseline, actual), 2),
        "beats_blended": bool(blended < mape(baseline, actual)),
        "real_n": int(real.sum()),
        "real_mape": round(real_only, 2),
        "baseline_real_mape": round(mape(baseline[real], actual[real]), 2),
        "beats_real": bool(real_only < mape(baseline[real], actual[real])),
    }
