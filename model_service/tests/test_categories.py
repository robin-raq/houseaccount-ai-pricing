"""Category coverage + normalization across the two naming schemes."""

import pytest

from pricing.categories import (
    PRODUCTION_VERTICALS,
    TRAINED_CATEGORIES,
    is_production,
    normalize_category,
)


def test_dataset_has_eighteen_trained_categories():
    assert len(TRAINED_CATEGORIES) == 18


def test_ten_production_verticals():
    assert len(PRODUCTION_VERTICALS) == 10


@pytest.mark.parametrize(
    "raw", ["Plumbing", "plumbing", "  PLUMBING ", "Pest Control", "pest-control"]
)
def test_production_categories_recognized_in_either_scheme(raw):
    assert is_production(raw) is True


@pytest.mark.parametrize("raw", ["Cleaning", "Landscaping", "HVAC", "hvac"])
def test_collapsed_production_categories_recognized(raw):
    # indoor/exterior cleaning -> "Cleaning"; landscaping-lawn/irrigation -> "Landscaping".
    assert is_production(raw) is True


@pytest.mark.parametrize("raw", ["Remodeling", "Roofing", "Painting", "Pool", "Auto", "Moving"])
def test_expansion_categories_are_out_of_production(raw):
    assert is_production(raw) is False


def test_blank_category_is_not_production():
    assert is_production("") is False
    assert is_production(None) is False


def test_normalize_kebabs_and_lowercases():
    assert normalize_category("Pest Control") == "pest-control"
    assert normalize_category("General_Contractor") == "general-contractor"
