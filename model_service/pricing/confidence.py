"""Confidence scoring and out-of-distribution (OOD) calibration.

Confidence is derived from the *width* of the conformal prediction interval relative
to the point estimate: a tight band means the model is sure, a wide band means it is
not. Three OOD conditions then force confidence below 0.5 — without rejecting or
capping the estimate itself, so the marketplace can route the booking appropriately.
"""

from __future__ import annotations

from dataclasses import dataclass

from .categories import is_production

# OOD thresholds (from Appendix A / the brief).
MIDPOINT_OOD_THRESHOLD = 5000.0  # ~95th percentile of training prices
INTERVAL_RATIO_THRESHOLD = 3.0  # interval wider than 3x the median observed range
OOD_CONFIDENCE_CEILING = 0.49  # forced ceiling when any OOD condition holds

# Maps relative interval width -> base confidence. Tunable against the dataset; the
# shape (monotonic decreasing in width) is fixed. rel = (hi - lo) / midpoint.
WIDTH_SCALE = 1.5
CONFIDENCE_FLOOR = 0.05


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class Confidence:
    value: float
    ood_reasons: tuple[str, ...]

    @property
    def is_ood(self) -> bool:
        return bool(self.ood_reasons)


def score(
    *,
    midpoint: float,
    estimate_lo: float,
    estimate_hi: float,
    service_category: str | None,
    median_interval: float,
) -> Confidence:
    """Compute calibrated confidence and any OOD reasons.

    ``median_interval`` is the median (hi - lo) observed on the training data,
    supplied by the trained artifact; it anchors the "3x median" OOD test.
    """
    width = max(estimate_hi - estimate_lo, 0.0)
    relative_width = width / midpoint if midpoint > 0 else float("inf")
    base = _clamp(1.0 - relative_width / WIDTH_SCALE, CONFIDENCE_FLOOR, 1.0)

    reasons: list[str] = []
    if midpoint > MIDPOINT_OOD_THRESHOLD:
        reasons.append("midpoint_above_5000")
    if median_interval > 0 and width > INTERVAL_RATIO_THRESHOLD * median_interval:
        reasons.append("interval_over_3x_median")
    if not is_production(service_category):
        reasons.append("category_outside_production_set")

    value = min(base, OOD_CONFIDENCE_CEILING) if reasons else base
    return Confidence(value=round(_clamp(value), 4), ood_reasons=tuple(reasons))
