"""Scope-signal extraction from a free-text job description.

The source data has no square-footage / fixture-count / complexity fields, so scope
must be read out of the homeowner's text. Two extractors share one output shape:

  * ``extract_scope_llm`` — an LLM (temp 0, cached) for rich, robust parsing.
  * ``extract_scope_fallback`` — deterministic regex/keyword parsing.

The model service always has the deterministic fallback, so it never hard-depends on
the LLM or an API key. ``extract_scope`` prefers the LLM and degrades gracefully.
"""

from __future__ import annotations

import re

_GALLONS = re.compile(r"(\d+)\s*-?\s*gal", re.I)
_STORIES = re.compile(r"(\d+)\s*-?\s*stor(?:y|ies)", re.I)
_SQFT = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet|sf)\b", re.I)
_COUNT = re.compile(r"(\d+)\s+(windows?|fixtures?|units?|rooms?|baths?|doors?|outlets?)", re.I)
_BEDROOMS = re.compile(r"(\d+)\s*-?\s*(?:br|bed(?:room)?s?)\b", re.I)

_CUSTOMER_SUPPLIES = re.compile(
    r"\b(you supply|i(?:'ll| will)? (?:supply|provide)|customer (?:supplies|provides))\b", re.I
)
_HIGH_COMPLEXITY = re.compile(
    r"\b(full|whole|gut|complete|renovat|remodel|rewire|repipe|new install)\w*", re.I
)
_LOW_COMPLEXITY = re.compile(r"\b(minor|small|quick|simple|touch[\s-]?up|patch|adjust)\w*", re.I)
_PREMIUM = re.compile(r"\b(premium|high[\s-]?end|luxury|custom)\b", re.I)
_ECONOMY = re.compile(r"\b(economy|budget|basic|cheap|standard grade)\b", re.I)


def _complexity(text: str) -> str:
    if _HIGH_COMPLEXITY.search(text):
        return "high"
    if _LOW_COMPLEXITY.search(text):
        return "low"
    return "medium"


def _material_tier(text: str) -> str:
    if _PREMIUM.search(text):
        return "premium"
    if _ECONOMY.search(text):
        return "economy"
    return "standard"


def extract_scope_fallback(description: str) -> dict[str, str]:
    """Deterministic scope signals — no network, no key. Always available."""
    text = description or ""
    scope: dict[str, str] = {
        "complexity": _complexity(text),
        "material_tier": _material_tier(text),
        "customer_supplies_parts": "yes" if _CUSTOMER_SUPPLIES.search(text) else "no",
    }
    if (match := _GALLONS.search(text)):
        scope["capacity_gallons"] = match.group(1)
    if (match := _SQFT.search(text)):
        scope["area_sqft"] = match.group(1).replace(",", "")
    if (match := _STORIES.search(text)):
        scope["stories"] = match.group(1)
    if (match := _BEDROOMS.search(text)):
        scope["bedrooms"] = match.group(1)
    if (match := _COUNT.search(text)):
        scope["quantity"] = f"{match.group(1)} {match.group(2).lower()}"
    return scope
