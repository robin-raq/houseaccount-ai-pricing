"""Ablation: does LLM scope extraction beat the deterministic fallback as features?

Precomputes (and disk-caches) LLM scope for every priced description, then re-scores
the leading configs over the same seeded grouped-CV splits with each scope source.

Run: uv run python scripts/ablate_llm_scope.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from pricing.data import load_clean, priced  # noqa: E402
from pricing.evaluation import mape  # noqa: E402
from pricing.llm_scope import extract_scope_llm  # noqa: E402
from pricing.model import DEFAULT_PARAMS, fit_residual_model, predict_prices  # noqa: E402

CACHE = Path("artifacts/llm_scope_cache.json")
SEEDS = [1, 7, 13, 21, 42]
N_SPLITS = 5
VERY_CONS = {
    **DEFAULT_PARAMS, "num_leaves": 5, "min_child_samples": 20,
    "reg_lambda": 8.0, "n_estimators": 250, "learning_rate": 0.02,
}
CONS = {
    **DEFAULT_PARAMS, "num_leaves": 7, "min_child_samples": 15,
    "reg_lambda": 5.0, "n_estimators": 300, "learning_rate": 0.02,
}


def build_scope_map(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict[str, str]] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rows = df.drop_duplicates("job_description")
    pending = [r for _, r in rows.iterrows() if r["job_description"] not in cache]
    print(f"unique priced descriptions: {len(rows)} | cached: {len(rows) - len(pending)} | "
          f"to extract: {len(pending)}")
    for i, row in enumerate(pending, 1):
        scope = extract_scope_llm(
            row["job_description"],
            service_category=row["service_category"],
            service_subtype=row["service_subtype"],
        )
        cache[row["job_description"]] = scope or {}
        if i % 20 == 0 or i == len(pending):
            print(f"  extracted {i}/{len(pending)}")
            CACHE.write_text(json.dumps(cache))
    CACHE.write_text(json.dumps(cache))
    return cache


def seeded_oof(df, fit_predict, seed):
    groups = pd.factorize(df["job_description"])[0]
    rng = np.random.RandomState(seed)
    fold_of = {g: i % N_SPLITS for i, g in enumerate(rng.permutation(np.unique(groups)))}
    fold = np.array([fold_of[g] for g in groups])
    oof = np.full(len(df), np.nan)
    for f in range(N_SPLITS):
        oof[fold == f] = fit_predict(df[fold != f], df[fold == f])
    return oof


def score(df, params, weight, shrink, scope_map):
    actual, real = df["final_price"].to_numpy(), df["is_real"].to_numpy()
    bl, re = [], []
    for seed in SEEDS:
        def fp(tr, te):
            fitted = fit_residual_model(
                tr, params, weight_by_uniqueness=weight, shrink=shrink, scope_map=scope_map
            )
            return predict_prices(fitted, te, scope_map)
        oof = seeded_oof(df, fp, seed)
        bl.append(mape(oof, actual))
        re.append(mape(oof[real], actual[real]))
    return np.array(bl), np.array(re)


def main():
    df = priced(load_clean())
    scope_map = build_scope_map(df)
    print("\nbaseline: blended 11.56 / real 35.87\n")
    print(f"{'config':40} {'blended':16} {'real':16}")
    configs = [
        ("verycons+weight+shrink0.7", VERY_CONS, True, 0.7),
        ("cons+weight+shrink0.7", CONS, True, 0.7),
        ("verycons+weight+shrink0.6", VERY_CONS, True, 0.6),
    ]
    for name, params, weight, shrink in configs:
        for src_label, sm in [("determ", None), ("LLM   ", scope_map)]:
            bl, re = score(df, params, weight, shrink, sm)
            print(f"{name + ' [' + src_label + ']':40} "
                  f"{bl.mean():5.2f} ± {bl.std():4.2f}    {re.mean():5.2f} ± {re.std():4.2f}")


if __name__ == "__main__":
    main()
