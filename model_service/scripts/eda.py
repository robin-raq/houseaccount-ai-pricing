"""One-off EDA to scout the dataset and resolve the real-vs-augmented split.

Run: uv run python scripts/eda.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parents[2] / "data" / "raw" / "houseaccount_pricing_sample.csv"


def ape(pred: pd.Series, actual: pd.Series) -> pd.Series:
    return (pred - actual).abs() / actual.abs() * 100.0


def main() -> None:
    df = pd.read_csv(CSV)
    print(f"shape: {df.shape}")
    print(f"columns: {list(df.columns)}\n")

    print("== null counts ==")
    print(df.isna().sum().to_string(), "\n")

    priced = df[df["final_price"].notna()].copy()
    print(f"priced rows (final_price present): {len(priced)}")

    # Reproduce the baseline: original_estimate vs final_price on priced rows.
    priced["ape"] = ape(priced["original_estimate"], priced["final_price"])
    print(f"BASELINE blended MAPE: {priced['ape'].mean():.2f}%  (target ~11.6)")
    print(f"BASELINE median APE : {priced['ape'].median():.2f}%  (target ~8.3)\n")

    # Real-vs-augmented hunt: is the APE distribution bimodal?
    print("== APE distribution on priced rows ==")
    for lo, hi in [(0, 0.5), (0.5, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, 1e9)]:
        n = ((priced["ape"] >= lo) & (priced["ape"] < hi)).sum()
        print(f"  APE [{lo:>4}, {hi:>5}) : {n:>4}")
    exact = (priced["final_price"] == priced["original_estimate"]).sum()
    near = (priced["ape"] < 0.5).sum()
    print(f"  final_price == original_estimate exactly: {exact}")
    print(f"  APE < 0.5% (near-synthetic): {near}")
    high = priced[priced["ape"] >= 20]
    print(f"  APE >= 20% (candidate 'real/hard'): {len(high)}")
    print(f"  APE >= 20% mean APE: {high['ape'].mean():.1f}%\n")

    # Duplicate descriptions (augmentation signature).
    dup = df["job_description"].duplicated(keep=False).sum()
    print(f"duplicated job_description rows: {dup}")
    print(f"unique job_description: {df['job_description'].nunique()} / {len(df)}\n")

    print("== category counts (all rows) ==")
    print(df["service_category"].value_counts().to_string(), "\n")
    print("== category counts (priced rows) ==")
    print(priced["service_category"].value_counts().to_string(), "\n")

    print("== final_price stats (priced) ==")
    print(priced["final_price"].describe(percentiles=[0.5, 0.9, 0.95, 0.99]).to_string())
    over_5k = (priced["final_price"] > 5000).sum()
    print(f"  final_price > $5000: {over_5k}")
    interval = (df["estimate_hi"] - df["estimate_lo"])
    print(f"  median (estimate_hi - estimate_lo): {interval.median():.2f}\n")

    print("== deadline values ==")
    print(df["deadline"].value_counts(dropna=False).to_string(), "\n")
    print("== booking_month range ==")
    print(f"  {df['booking_month'].min()} .. {df['booking_month'].max()}")
    print(f"  unique zips: {df['zip_code'].nunique()}")
    print(f"  unique subtypes: {df['service_subtype'].nunique()}")

    # A possible 'real' signal: look at whether high-APE rows cluster by anything.
    print("\n== high-APE (>=20%) rows by category ==")
    print(high["service_category"].value_counts().to_string())
    print(f"\nIs there a ~27-row natural 'real' cut? rows with APE>=25%: "
          f"{(priced['ape'] >= 25).sum()}, >=30%: {(priced['ape'] >= 30).sum()}")


if __name__ == "__main__":
    sys.exit(main())
