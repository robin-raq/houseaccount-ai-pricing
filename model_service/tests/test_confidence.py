"""Confidence + OOD calibration rules (Appendix A)."""

from pricing.confidence import OOD_CONFIDENCE_CEILING, score

MEDIAN_INTERVAL = 200.0  # representative median (hi - lo) for these tests


def _score(**kw):
    base = dict(
        midpoint=1825.0,
        estimate_lo=1450.0,
        estimate_hi=2200.0,
        service_category="Plumbing",
        median_interval=MEDIAN_INTERVAL,
    )
    base.update(kw)
    return score(**base)


def test_in_distribution_estimate_is_confident_and_not_ood():
    result = _score(estimate_lo=1700.0, estimate_hi=1950.0)  # tight band, production
    assert not result.is_ood
    assert result.value >= 0.5
    assert 0.0 <= result.value <= 1.0


def test_tighter_interval_yields_higher_confidence():
    tight = _score(estimate_lo=1750.0, estimate_hi=1900.0)
    wide = _score(estimate_lo=1200.0, estimate_hi=2600.0)
    assert tight.value > wide.value


def test_midpoint_above_5000_forces_low_confidence_without_capping():
    result = _score(midpoint=8400.0, estimate_lo=7000.0, estimate_hi=9800.0)
    assert "midpoint_above_5000" in result.ood_reasons
    assert result.value < 0.5
    assert result.value <= OOD_CONFIDENCE_CEILING


def test_interval_wider_than_3x_median_forces_low_confidence():
    # width 900 > 3 * 200 = 600 -> OOD, even though midpoint is small.
    result = _score(midpoint=1200.0, estimate_lo=750.0, estimate_hi=1650.0)
    assert "interval_over_3x_median" in result.ood_reasons
    assert result.value < 0.5


def test_non_production_category_forces_low_confidence():
    result = _score(service_category="Remodeling", estimate_lo=1700.0, estimate_hi=1950.0)
    assert "category_outside_production_set" in result.ood_reasons
    assert result.value < 0.5


def test_confidence_is_clamped_to_unit_interval():
    result = _score(midpoint=1.0, estimate_lo=0.0, estimate_hi=10000.0)
    assert 0.0 <= result.value <= 1.0
