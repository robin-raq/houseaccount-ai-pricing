"""The LLM scope cache is bounded, and extraction no-ops without a key."""

import pricing.llm_scope as llm_scope


def test_cache_evicts_oldest_past_cap(monkeypatch):
    monkeypatch.setattr(llm_scope, "_MAX_CACHE", 3)
    llm_scope._cache.clear()
    for i in range(6):
        llm_scope._remember(f"k{i}", {"complexity": "low"})
    assert len(llm_scope._cache) == 3
    assert set(llm_scope._cache) == {"k3", "k4", "k5"}  # the three most recent survive


def test_extract_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm_scope.extract_scope_llm("any description") is None
