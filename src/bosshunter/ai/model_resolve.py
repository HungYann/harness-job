"""Fuzzy model name resolution for OneAPI-style relay services."""

import os
import re
import httpx

_cache: dict[str, str] = {}


def _normalize(name: str) -> str:
    """Normalize model name for comparison: lowercase, strip spaces/hyphens/dots."""
    return re.sub(r"[\s\-._]+", "", name.lower())


def _extract_tokens(name: str) -> set[str]:
    """Extract meaningful tokens (words and version numbers) from model name."""
    return set(re.findall(r"[a-z]+|\d+(?:\.\d+)?", name.lower()))


def resolve_model(model: str, config: dict) -> str:
    """Resolve user-specified model name to actual available model name.

    Queries /v1/models endpoint and finds the best fuzzy match.
    Returns original model name if resolution fails or no relay is configured.
    """
    if model in _cache:
        return _cache[model]

    ai_cfg = config.get("ai", {})
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or ai_cfg.get("base_url")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or ai_cfg.get("api_key")

    if not base_url or not api_key:
        return model

    try:
        r = httpx.get(
            f"{base_url.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.status_code != 200:
            return model

        available = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return model

    # Exact match
    if model in available:
        _cache[model] = model
        return model

    # Fuzzy match: normalize both sides and compare
    norm_input = _normalize(model)
    for candidate in available:
        if _normalize(candidate) == norm_input:
            _cache[model] = candidate
            return candidate

    # Partial match: check if normalized input is contained or contains
    for candidate in available:
        nc = _normalize(candidate)
        if norm_input in nc or nc in norm_input:
            _cache[model] = candidate
            return candidate

    # Token-based match: same key tokens regardless of order
    input_tokens = _extract_tokens(model)
    best_candidate = None
    best_overlap = 0
    for candidate in available:
        candidate_tokens = _extract_tokens(candidate)
        overlap = len(input_tokens & candidate_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_candidate = candidate

    if best_candidate and best_overlap >= max(2, len(input_tokens) - 1):
        _cache[model] = best_candidate
        return best_candidate

    # No match found, return original
    return model
