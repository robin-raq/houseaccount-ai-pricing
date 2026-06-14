"""Deterministic scope extraction (the always-available fallback)."""

from pricing.scope import extract_scope_fallback


def test_extracts_capacity_and_supplies_flag():
    scope = extract_scope_fallback("Replace 50-gallon gas water heater (you supply the unit)")
    assert scope["capacity_gallons"] == "50"
    assert scope["customer_supplies_parts"] == "yes"


def test_extracts_count_and_stories():
    scope = extract_scope_fallback("Exterior window wash, 2-story, 20 windows")
    assert scope["stories"] == "2"
    assert scope["quantity"] == "20 windows"


def test_extracts_area_and_high_complexity():
    scope = extract_scope_fallback("Full gut renovation of a 3,200 sq ft home")
    assert scope["area_sqft"] == "3200"
    assert scope["complexity"] == "high"


def test_defaults_are_sensible():
    scope = extract_scope_fallback("Bathroom walls painting project")
    assert scope["complexity"] == "medium"
    assert scope["material_tier"] == "standard"
    assert scope["customer_supplies_parts"] == "no"
