"""Load and clean the historical pricing dataset.

Adds the derived columns the model and the evaluation both rely on: canonical
deadline buckets, an urgency score, a parsed booking month, a ZIP-3 region, and the
``is_real`` flag (a globally-unique job_description marks a genuine historical job
rather than an augmented template — see EDA / model card).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_CSV = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "houseaccount_pricing_sample.csv"
)

# Canonicalize the 7 observed deadline strings into the 4 Appendix A buckets (+ unknown).
DEADLINE_BUCKETS: dict[str, str] = {
    "As soon as possible": "asap",
    "Within 1 week": "within_2_weeks",
    "Within 2 weeks": "within_2_weeks",
    "Within 1-2 weeks": "within_2_weeks",
    "Within 1 month": "within_1_month",
    "I'm flexible": "flexible",
    "Flexible": "flexible",
}
_URGENCY = {"asap": 0, "within_2_weeks": 1, "within_1_month": 2, "flexible": 3, "unknown": 1}


def deadline_bucket(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    return DEADLINE_BUCKETS.get(value.strip(), "unknown")


def load_raw(path: Path | str | None = None) -> pd.DataFrame:
    return pd.read_csv(path or REPO_CSV, dtype={"zip_code": str})


def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["zip_code"] = out["zip_code"].astype(str).str.zfill(5).str.slice(0, 5)
    out["zip3"] = out["zip_code"].str.slice(0, 3)
    out["deadline_bucket"] = out["deadline"].map(deadline_bucket)
    out["urgency"] = out["deadline_bucket"].map(_URGENCY).astype("int8")
    out["month"] = pd.to_datetime(out["booking_month"], format="%Y-%m", errors="coerce").dt.month
    out["month"] = out["month"].fillna(0).astype("int8")
    out["estimate_width"] = (out["estimate_hi"] - out["estimate_lo"]).clip(lower=0)
    # A globally-unique description marks a real historical job (vs an augmented template).
    freq = out["job_description"].value_counts()
    out["desc_freq"] = out["job_description"].map(freq).astype("int16")
    out["is_real"] = out["desc_freq"].eq(1)
    return out


def load_clean(path: Path | str | None = None) -> pd.DataFrame:
    return clean(load_raw(path))


def priced(df: pd.DataFrame) -> pd.DataFrame:
    # Positive prices only — the log-space training and conformal math require > 0.
    return df[df["final_price"].notna() & (df["final_price"] > 0)].copy()
