"""Reproducible model bake-off: many configs x multiple seeded grouped-CV splits.

Selection favors a ROBUST margin under both baselines (mean - std), not a single lucky
split — the finalist test is a held-out real set, so generalization beats CV-squeezing.

Run: uv run python scripts/bakeoff.py
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from pricing.data import load_clean, priced  # noqa: E402
from pricing.evaluation import BASELINE_BLENDED, BASELINE_REAL, mape  # noqa: E402
from pricing.model import DEFAULT_PARAMS, fit_residual_model, predict_prices  # noqa: E402

SEEDS = [1, 7, 13, 21, 42]
N_SPLITS = 5
CONSERVATIVE = {
    **DEFAULT_PARAMS, "num_leaves": 7, "min_child_samples": 15,
    "reg_lambda": 5.0, "n_estimators": 300, "learning_rate": 0.02,
}
VERY_CONS = {
    **DEFAULT_PARAMS, "num_leaves": 5, "min_child_samples": 20,
    "reg_lambda": 8.0, "n_estimators": 250, "learning_rate": 0.02,
}


def make_fit_predict(params, *, weight, shrink):
    def fit_predict(train, test):
        fitted = fit_residual_model(train, params, weight_by_uniqueness=weight, shrink=shrink)
        return predict_prices(fitted, test)
    return fit_predict


def seeded_oof(df, fit_predict, seed):
    groups = pd.factorize(df["job_description"])[0]
    rng = np.random.RandomState(seed)
    perm = rng.permutation(np.unique(groups))
    fold_of = {g: i % N_SPLITS for i, g in enumerate(perm)}
    fold = np.array([fold_of[g] for g in groups])
    oof = np.full(len(df), np.nan)
    for f in range(N_SPLITS):
        oof[fold == f] = fit_predict(df[fold != f], df[fold == f])
    return oof


def score(df, fit_predict):
    actual = df["final_price"].to_numpy()
    real = df["is_real"].to_numpy()
    blended, real_only = [], []
    for seed in SEEDS:
        oof = seeded_oof(df, fit_predict, seed)
        blended.append(mape(oof, actual))
        real_only.append(mape(oof[real], actual[real]))
    return np.array(blended), np.array(real_only)


def main():
    df = priced(load_clean())
    configs = {
        "default": (DEFAULT_PARAMS, False, 1.0),
        "default+shrink0.6": (DEFAULT_PARAMS, False, 0.6),
        "conservative": (CONSERVATIVE, False, 1.0),
        "conservative+weight": (CONSERVATIVE, True, 1.0),
        "conservative+shrink0.6": (CONSERVATIVE, False, 0.6),
        "conservative+weight+shrink0.7": (CONSERVATIVE, True, 0.7),
        "conservative+weight+shrink0.5": (CONSERVATIVE, True, 0.5),
        "verycons+weight+shrink0.7": (VERY_CONS, True, 0.7),
        "verycons+weight+shrink0.6": (VERY_CONS, True, 0.6),
        "verycons+shrink0.6": (VERY_CONS, False, 0.6),
    }
    print(f"baseline: blended {BASELINE_BLENDED}% / real {BASELINE_REAL}% "
          f"(reproduced 11.56 / 35.87)\n")
    print(f"{'config':34} {'blended mean±std':18} {'real mean±std':18} robust")
    rows = []
    for name, (params, weight, shrink) in configs.items():
        bl, re = score(df, make_fit_predict(params, weight=weight, shrink=shrink))
        # robust margin: how far mean+std stays under each baseline (higher = safer)
        margin = min(11.56 - (bl.mean() + bl.std()), 35.87 - (re.mean() + re.std()))
        rows.append((name, bl, re, margin))
        flag = "OK" if (bl.mean() < 11.56 and re.mean() < 35.87) else "-"
        print(f"{name:34} {bl.mean():5.2f} ± {bl.std():4.2f}      "
              f"{re.mean():5.2f} ± {re.std():4.2f}      {margin:+5.2f} {flag}")
    best = max(rows, key=lambda r: r[3])
    print(f"\nMOST ROBUST: {best[0]}  (blended {best[1].mean():.2f}, "
          f"real {best[2].mean():.2f}, robust margin {best[3]:+.2f})")


if __name__ == "__main__":
    main()
