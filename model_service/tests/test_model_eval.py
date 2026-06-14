"""The core promise: the model beats both MAPE baselines (grouped CV, deterministic).

Uses the deterministic scope source so the test needs no API key and is reproducible.
Skips when the dataset is not present locally (it is gitignored — client data).
"""

import warnings

import pytest

from pricing.data import REPO_CSV, load_clean, priced
from pricing.evaluation import mape
from pricing.training import ModelConfig, grouped_oof

pytestmark = pytest.mark.skipif(not REPO_CSV.exists(), reason="dataset not present locally")

BASELINE_BLENDED = 11.56
BASELINE_REAL = 35.87


def test_deterministic_model_beats_both_baselines():
    warnings.filterwarnings("ignore")
    df = priced(load_clean())
    config = ModelConfig(version="test", use_llm_scope=False)
    oof = grouped_oof(df, config, scope_map=None, seed=42)

    actual = df["final_price"].to_numpy()
    real = df["is_real"].to_numpy()
    assert mape(oof, actual) < BASELINE_BLENDED
    assert mape(oof[real], actual[real]) < BASELINE_REAL


def test_real_subset_matches_unique_descriptions():
    df = priced(load_clean())
    # The real-job subset is the globally-unique descriptions (~27-31 per the brief).
    assert 20 <= int(df["is_real"].sum()) <= 40
