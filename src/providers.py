"""Resolve one OpenAI-compatible endpoint for the application; no network calls."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    base_url: str
    api_key: str = field(repr=False)
    model: str


def resolve_provider(env: Mapping[str, str] | None = None) -> ProviderConfig:
    """Legacy OPENAI_* variables remain supported when no provider is selected."""
    values = os.environ if env is None else env
    provider = values.get("LLM_PROVIDER", "custom").strip().lower()
    if provider == "deepseek":
        key = values.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise ValueError("LLM_PROVIDER=deepseek requires DEEPSEEK_API_KEY")
        return ProviderConfig(
            provider,
            "https://api.deepseek.com",
            key,
            values.get("DEEPSEEK_MODEL") or "deepseek-flash",
        )
    if provider == "ollama":
        return ProviderConfig(
            provider,
            values.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1",
            "ollama",
            values.get("OLLAMA_MODEL") or "qwen2.5:3b",
        )
    if provider == "custom":
        return ProviderConfig(
            provider,
            values.get("OPENAI_BASE_URL") or "http://localhost:11434/v1",
            values.get("OPENAI_API_KEY") or "dummy",
            values.get("MODEL_NAME") or "qwen2.5:3b",
        )
    raise ValueError("LLM_PROVIDER must be deepseek, ollama, or custom")
