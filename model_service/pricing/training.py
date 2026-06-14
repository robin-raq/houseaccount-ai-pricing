"""Fit the final pricing model and calibrate its conformal interval.

The interval half-width ``conformal_q`` is taken from grouped out-of-fold residuals
(honest, leakage-free), not from in-sample fit. The result is a serving-ready
``TrainedModel``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .llm_scope import extract_scope_llm
from .model import DEFAULT_PARAMS, fit_residual_model, predict_prices, relative_band
from .serving import TrainedModel

WINNER_PARAMS = {
    **DEFAULT_PARAMS, "num_leaves": 5, "min_child_samples": 20,
    "reg_lambda": 8.0, "n_estimators": 250, "learning_rate": 0.02,
}


@dataclass
class ModelConfig:
    version: str
    params: dict = field(default_factory=lambda: dict(WINNER_PARAMS))
    weight: bool = True
    shrink: float = 0.7
    coverage: float = 0.80
    use_llm_scope: bool = True


def precompute_scope_map(df: pd.DataFrame, cache_path: Path | str) -> dict[str, dict[str, str]]:
    """Extract (and disk-cache) LLM scope for every unique description."""
    cache_path = Path(cache_path)
    cache: dict[str, dict] = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    changed = False
    for _, row in df.drop_duplicates("job_description").iterrows():
        description = row["job_description"]
        if description in cache:
            continue
        scope = extract_scope_llm(
            description,
            service_category=row.get("service_category"),
            service_subtype=row.get("service_subtype"),
        )
        cache[description] = scope or {}
        changed = True
    if changed:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache))
    return cache


def grouped_oof(
    df: pd.DataFrame, config: ModelConfig, scope_map, seed: int = 42, n_splits: int = 5
):
    groups = pd.factorize(df["job_description"])[0]
    rng = np.random.RandomState(seed)
    fold_of = {g: i % n_splits for i, g in enumerate(rng.permutation(np.unique(groups)))}
    fold = np.array([fold_of[g] for g in groups])
    oof = np.full(len(df), np.nan)
    for current in range(n_splits):
        fitted = fit_residual_model(
            df[fold != current], config.params,
            weight_by_uniqueness=config.weight, shrink=config.shrink, scope_map=scope_map,
        )
        oof[fold == current] = predict_prices(fitted, df[fold == current], scope_map)
    return oof


def build_trained_model(
    df_priced: pd.DataFrame, config: ModelConfig, scope_map=None
) -> TrainedModel:
    fitted = fit_residual_model(
        df_priced, config.params, weight_by_uniqueness=config.weight,
        shrink=config.shrink, scope_map=scope_map,
    )
    oof = grouped_oof(df_priced, config, scope_map)
    actual = df_priced["final_price"].to_numpy()
    band = relative_band(df_priced)
    # Normalized (Mondrian-style) nonconformity: scale residual by the prior's band so
    # the interval half-width adapts to per-job difficulty.
    nonconformity = np.abs(np.log(actual) - np.log(np.clip(oof, 1.0, None))) / band
    conformal_q = float(np.quantile(nonconformity, config.coverage))

    # OOD base = the dataset's "median observed range" (estimate_hi - estimate_lo).
    observed_range = (df_priced["estimate_hi"] - df_priced["estimate_lo"]).median()
    category_prior = df_priced.groupby("service_category")["original_estimate"].median().to_dict()
    return TrainedModel(
        fitted=fitted,
        conformal_q=conformal_q,
        median_interval=float(observed_range),
        model_version=config.version,
        category_prior={str(k): float(v) for k, v in category_prior.items()},
        global_prior=float(df_priced["original_estimate"].median()),
        use_llm_scope=config.use_llm_scope,
    )
