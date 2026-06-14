"""The trained, serialized model serves calibrated estimates (protocol + OOD)."""

from pathlib import Path

import pytest

from pricing.estimator import PricingModel, estimate
from pricing.loader import ARTIFACT_PATH, load_model
from pricing.schemas import PredictRequest

pytestmark = pytest.mark.skipif(
    not Path(ARTIFACT_PATH).exists(), reason="trained model artifact not present"
)


def _request(**kw) -> PredictRequest:
    base = dict(
        job_id="t", service_category="Plumbing", zip_code="78704",
        job_description="Replace 50-gallon gas water heater",
        original_estimate=1850.0, original_estimate_lo=1400.0, original_estimate_hi=2300.0,
    )
    base.update(kw)
    return PredictRequest(**base)


def test_trained_model_implements_protocol():
    assert isinstance(load_model(), PricingModel)


def test_in_distribution_estimate_is_ordered_and_confident():
    response = estimate(_request(), load_model(), use_llm=False)
    assert response.estimate_lo <= response.estimate_midpoint <= response.estimate_hi
    assert response.confidence >= 0.5
    assert not response.ood_reasons


def test_non_production_category_is_low_confidence_but_not_rejected():
    response = estimate(
        _request(service_category="Remodeling", original_estimate=90000.0,
                 original_estimate_lo=70000.0, original_estimate_hi=110000.0),
        load_model(), use_llm=False,
    )
    assert response.confidence < 0.5
    assert "category_outside_production_set" in response.ood_reasons
    assert response.estimate_midpoint > 0  # passed through, not rejected


def test_missing_prior_is_imputed_and_still_priced():
    response = estimate(
        _request(service_category="Cleaning", original_estimate=None,
                 original_estimate_lo=None, original_estimate_hi=None,
                 job_description="Standard 3 bedroom house deep clean"),
        load_model(), use_llm=False,
    )
    assert response.estimate_lo <= response.estimate_midpoint <= response.estimate_hi
