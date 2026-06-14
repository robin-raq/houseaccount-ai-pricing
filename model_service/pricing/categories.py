"""Service-category coverage and normalization.

The training dataset names categories in title-case ("Plumbing"); the production
seed file uses kebab-case slugs ("plumbing"). Several production slugs also collapse
into one dataset category (indoor/exterior cleaning -> "Cleaning"). We normalize both
schemes to a single canonical key so the out-of-distribution confidence rule
("category outside the 10 production verticals") fires correctly either way.
"""

from __future__ import annotations

# The 18 categories present in the training dataset (title-case).
TRAINED_CATEGORIES: frozenset[str] = frozenset(
    {
        "Appliance Repair", "Auto", "Chimney", "Cleaning", "Electrical", "Exterior",
        "Flooring", "General Contractor", "Handyman", "HVAC", "Landscaping", "Moving",
        "Painting", "Pest Control", "Plumbing", "Pool", "Remodeling", "Roofing",
    }
)

# The 10 current production verticals (kebab-case slugs from the seed file).
PRODUCTION_VERTICALS: frozenset[str] = frozenset(
    {
        "electrical", "exterior-cleaning", "handyman", "hvac", "indoor-cleaning",
        "irrigation", "landscaping-lawn", "pest-control", "plumbing",
        "tick-mosquito-treatment",
    }
)

# Canonical production keys, normalized. Includes the kebab slugs above plus the
# normalized title-case dataset names that map onto a production vertical. This is
# the category-coverage bridge documented in the model card.
_PRODUCTION_KEYS: frozenset[str] = PRODUCTION_VERTICALS | frozenset(
    {"cleaning", "landscaping", "pest-control", "plumbing", "electrical", "hvac", "handyman"}
)


# Production kebab slugs that collapse onto a different dataset category than their
# own normalized form (several production verticals fold into one dataset category).
_SLUG_TO_CATEGORY: dict[str, str] = {
    "indoor-cleaning": "cleaning",
    "exterior-cleaning": "cleaning",
    "landscaping-lawn": "landscaping",
    "irrigation": "landscaping",
    "tick-mosquito-treatment": "pest-control",
}


def normalize_category(raw: str | None) -> str:
    """Lower-case, trim, and kebab-ify a category from either naming scheme."""
    if not raw:
        return ""
    return "-".join(raw.strip().lower().replace("_", " ").replace("-", " ").split())


def canonical_category(raw: str | None) -> str:
    """Map any category — title-case dataset name or kebab production slug — onto the
    single normalized vocabulary the model is trained on, so the feature, the prior
    lookup, and the OOD check all agree.
    """
    normalized = normalize_category(raw)
    return _SLUG_TO_CATEGORY.get(normalized, normalized)


def is_production(raw: str | None) -> bool:
    """True if the category is one of the 10 current production verticals.

    Out-of-production categories still get an estimate, but with confidence forced
    below 0.5 by the calibration layer.
    """
    return normalize_category(raw) in _PRODUCTION_KEYS
