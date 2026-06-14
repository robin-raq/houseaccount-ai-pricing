"""LLM-based scope extraction (optional enrichment over the deterministic fallback).

Pinned to temperature 0 and cached by a hash of the inputs so repeated/eval requests
are deterministic. Returns ``None`` whenever the key is absent, the call errors, or it
takes too long — the caller then uses ``extract_scope_fallback``. The model never
prices the job; it only structures the description.
"""

from __future__ import annotations

import hashlib
import json
import os

_MODEL = os.environ.get("PRICING_SCOPE_MODEL", "gpt-4o-mini")
_TIMEOUT_S = float(os.environ.get("PRICING_SCOPE_TIMEOUT_S", "1.5"))
_cache: dict[str, dict[str, str]] = {}

_SYSTEM = (
    "You convert a homeowner's free-text home-service request into structured scope "
    "signals used to price the job. Return a flat JSON object of string values only. "
    "Use keys when present: complexity (low|medium|high), material_tier "
    "(economy|standard|premium), customer_supplies_parts (yes|no), est_labor_hours, "
    "area_sqft, capacity_gallons, stories, bedrooms, quantity, access_difficulty. "
    "Never include a price. Omit keys you cannot infer."
)


def _key(category: str | None, subtype: str | None, description: str) -> str:
    raw = f"{category}|{subtype}|{description}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extract_scope_llm(
    description: str,
    *,
    service_category: str | None = None,
    service_subtype: str | None = None,
) -> dict[str, str] | None:
    """Best-effort structured scope from the LLM, or ``None`` to trigger the fallback."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None

    cache_key = _key(service_category, service_subtype, description)
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        from openai import OpenAI

        client = OpenAI(timeout=_TIMEOUT_S)
        user = f"Category: {service_category}\nSubtype: {service_subtype}\nRequest: {description}"
        completion = client.chat.completions.create(
            model=_MODEL,
            temperature=0,
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
    except Exception:
        return None

    scope = {str(key): str(value) for key, value in payload.items() if value is not None}
    _cache[cache_key] = scope
    return scope
