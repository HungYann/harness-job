"""Unified AI client — routes to Anthropic or OpenAI-compatible providers.

Provider selection via config.yaml  ai.provider:
  anthropic  (default) — Claude models, uses ANTHROPIC_API_KEY
  deepseek             — DeepSeek models, uses DEEPSEEK_API_KEY
  openai               — OpenAI models, uses OPENAI_API_KEY
  custom               — Any OpenAI-compatible relay, uses ai.base_url + ai.api_key

All four share the same call_ai() entry point so callers don't need to
know which SDK is in use.
"""

from __future__ import annotations

import os
from typing import Any

from bosshunter.ai.model_resolve import resolve_model


# ── Defaults per provider ──────────────────────────────────────────────────
_PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "model":    "claude-sonnet-4-6",
        "base_url": None,
        "key_envs": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"],
    },
    "deepseek": {
        "model":    "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "key_envs": ["DEEPSEEK_API_KEY"],
    },
    "openai": {
        "model":    "gpt-4o",
        "base_url": None,
        "key_envs": ["OPENAI_API_KEY"],
    },
    "custom": {
        "model":    "gpt-4o",
        "base_url": None,
        "key_envs": [],
    },
}


def _get_api_key(ai_cfg: dict, provider: str) -> str | None:
    """Resolve API key from env vars (provider-specific order) then config."""
    defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["custom"])
    for env in defaults["key_envs"]:
        val = os.environ.get(env)
        if val:
            return val
    return ai_cfg.get("api_key") or None


def call_ai(prompt: str, config: dict, max_tokens: int = 512) -> str | None:
    """Call the configured AI provider and return the response text.

    Returns None on any failure (missing key, network error, etc.).
    """
    ai_cfg = config.get("ai", {})
    provider = ai_cfg.get("provider", "anthropic").lower()

    if provider == "anthropic":
        return _call_anthropic(prompt, ai_cfg, config, max_tokens)
    elif provider in ("deepseek", "openai", "custom"):
        return _call_openai_compat(prompt, ai_cfg, config, provider, max_tokens)
    else:
        # unknown provider → try anthropic as fallback
        return _call_anthropic(prompt, ai_cfg, config, max_tokens)


# ── Anthropic ──────────────────────────────────────────────────────────────

def _call_anthropic(prompt: str, ai_cfg: dict, config: dict, max_tokens: int) -> str | None:
    try:
        import anthropic
    except ImportError:
        return None

    api_key = _get_api_key(ai_cfg, "anthropic")
    if not api_key:
        return None

    model = resolve_model(ai_cfg.get("model", "claude-sonnet-4-6"), config)
    base_url = (
        os.environ.get("ANTHROPIC_BASE_URL")
        or ai_cfg.get("base_url")
    )

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    try:
        client = anthropic.Anthropic(**kwargs)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if hasattr(block, "text"):
                return block.text.strip()
        return None
    except Exception:
        return None


# ── OpenAI-compatible (DeepSeek / OpenAI / custom relay) ──────────────────

def _call_openai_compat(
    prompt: str,
    ai_cfg: dict,
    config: dict,
    provider: str,
    max_tokens: int,
) -> str | None:
    try:
        from openai import OpenAI
    except ImportError:
        return None

    defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["custom"])

    api_key = _get_api_key(ai_cfg, provider)
    if not api_key:
        return None

    base_url = (
        os.environ.get("OPENAI_BASE_URL")          # generic override
        or ai_cfg.get("base_url")                   # config file
        or defaults["base_url"]                     # provider default
    )

    model = ai_cfg.get("model") or defaults["model"]

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    try:
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None
