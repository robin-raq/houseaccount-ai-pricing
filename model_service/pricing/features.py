"""Feature engineering for the correction model.

The previous model's output (``original_estimate`` and its lo/hi band) is the prior;
the model learns a residual on top of it using signals the prior ignored — scope read
from the description, ZIP region, subtype, urgency, and seasonality.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .scope import extract_scope_fallback

CATEGORICAL = ["service_category", "service_subtype", "zip3", "deadline_bucket"]
_COMPLEXITY = {"low": 0.0, "medium": 1.0, "high": 2.0}
_MATERIAL = {"economy": 0.0, "standard": 1.0, "premium": 2.0}


def _num(scope: dict[str, str], key: str) -> float:
    try:
        return float(scope.get(key, "nan"))
    except (TypeError, ValueError):
        return np.nan


def scope_to_numeric(scope: dict[str, str]) -> dict[str, float]:
    """Map a scope dict (from either extractor) to numeric model features."""
    quantity = str(scope.get("quantity", "0")).split(" ")[0]
    return {
        "complexity": _COMPLEXITY.get(scope.get("complexity", "medium"), 1.0),
        "material_tier": _MATERIAL.get(scope.get("material_tier", "standard"), 1.0),
        "access_difficulty": _COMPLEXITY.get(scope.get("access_difficulty", "medium"), 1.0),
        "customer_supplies": 1.0 if scope.get("customer_supplies_parts") == "yes" else 0.0,
        "est_labor_hours": _num(scope, "est_labor_hours"),
        "area_sqft": _num(scope, "area_sqft"),
        "capacity_gallons": _num(scope, "capacity_gallons"),
        "stories": _num(scope, "stories"),
        "bedrooms": _num(scope, "bedrooms"),
        "quantity_num": float(quantity) if quantity.isdigit() else np.nan,
    }


def _row_scope(description: str, scope_map: dict[str, dict[str, str]] | None) -> dict[str, str]:
    if scope_map is not None and description in scope_map:
        return scope_map[description]
    return extract_scope_fallback(description)


def build_features(
    df: pd.DataFrame, scope_map: dict[str, dict[str, str]] | None = None
) -> pd.DataFrame:
    """Return the model feature matrix (one row per input row).

    ``scope_map`` optionally supplies pre-extracted (e.g. LLM) scope per description;
    without it, the deterministic fallback extractor is used.
    """
    out = pd.DataFrame(index=df.index)

    prior = df["original_estimate"].clip(lower=1.0)
    out["log_prior"] = np.log(prior)
    out["log_estimate_lo"] = np.log(df["estimate_lo"].clip(lower=1.0))
    out["log_estimate_hi"] = np.log(df["estimate_hi"].clip(lower=1.0))
    out["rel_band"] = (df["estimate_hi"] - df["estimate_lo"]) / prior

    out["urgency"] = df["urgency"].astype(float)
    out["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)
    out["desc_len"] = df["job_description"].str.len().astype(float)
    out["desc_words"] = df["job_description"].str.split().map(len).astype(float)
    # Provenance: a repeated description is an augmented template (model should not
    # over-correct it); a unique description is a real job (and every live request
    # is unique, so production always runs in "real" mode).
    out["is_augmented"] = (df["desc_freq"] >= 2).astype(float)

    scope = df["job_description"].map(
        lambda desc: scope_to_numeric(_row_scope(desc, scope_map))
    ).apply(pd.Series)
    out = out.join(scope)

    # Categoricals stay as plain strings here; a stable vocabulary is applied later
    # (see align_categoricals) so train/test/serve share the same category codes.
    for column in CATEGORICAL:
        out[column] = df[column].astype("string").astype(object)
    return out


def learn_categories(features: pd.DataFrame) -> dict[str, pd.Index]:
    """Freeze the category vocabulary from the training feature matrix."""
    return {column: pd.Index(sorted(features[column].dropna().unique())) for column in CATEGORICAL}


def align_categoricals(features: pd.DataFrame, levels: dict[str, pd.Index]) -> pd.DataFrame:
    """Cast categoricals to the frozen vocabulary so codes match what the model learned."""
    aligned = features.copy()
    for column, categories in levels.items():
        # Map values unseen in training to NaN first (the model handles missing codes).
        known = aligned[column].where(aligned[column].isin(categories))
        aligned[column] = pd.Categorical(known, categories=categories)
    return aligned
