"""Estimator orchestration against the injected stub model."""

from pricing.estimator import StubModel, estimate
from pricing.schemas import PredictRequest


def _request(**kw) -> PredictRequest:
    base = dict(
        job_id="t1",
        service_category="Plumbing",
        zip_code="78704",
        job_description="Replace 50-gallon gas water heater",
    )
    base.update(kw)
    return PredictRequest(**base)


def test_returns_ordered_interval_and_echoes_job_id():
    response = estimate(_request(original_estimate=1825.0), StubModel(), use_llm=False)
    assert response.job_id == "t1"
    assert response.estimate_lo <= response.estimate_midpoint <= response.estimate_hi
    assert 0.0 <= response.confidence <= 1.0
    assert response.model_version == "stub-0"


def test_scope_signals_are_attached():
    response = estimate(_request(), StubModel(), use_llm=False)
    assert response.scope["capacity_gallons"] == "50"


def test_non_production_category_is_flagged_ood():
    response = estimate(
        _request(service_category="Remodeling", original_estimate=400.0), StubModel(), use_llm=False
    )
    assert "category_outside_production_set" in response.ood_reasons
    assert response.confidence < 0.5
