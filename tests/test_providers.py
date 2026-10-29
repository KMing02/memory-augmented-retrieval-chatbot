import pytest
from src.providers import resolve_provider


def test_deepseek_configuration_is_explicit_and_secret_is_not_in_repr():
    config = resolve_provider({"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "synthetic-key"})
    assert config.base_url == "https://api.deepseek.com"
    assert config.model == "deepseek-flash"
    assert "synthetic-key" not in repr(config)


def test_missing_deepseek_key_fails_before_network():
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        resolve_provider({"LLM_PROVIDER": "deepseek"})


def test_ollama_ignores_unrelated_hosted_credentials():
    config = resolve_provider({"LLM_PROVIDER": "ollama", "OPENAI_API_KEY": "unused"})
    assert config.api_key == "ollama"
    assert config.model == "qwen2.5:3b"
    assert config.base_url == "http://localhost:11434/v1"


def test_legacy_and_custom_configuration():
    values = {
        "OPENAI_BASE_URL": "http://localhost:1234/v1",
        "OPENAI_API_KEY": "dummy",
        "MODEL_NAME": "example-model",
    }
    assert resolve_provider(values) == resolve_provider({**values, "LLM_PROVIDER": "custom"})
    assert resolve_provider(values).model == "example-model"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        resolve_provider({"LLM_PROVIDER": "unknown"})


def test_application_and_memory_share_resolved_configuration(monkeypatch):
    from src.config import AppConfig
    from src.memory.langmem_structured import LangMemBackendConfig
    from src.connection_guard import connection_guard_from_env

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "example-model")
    app, memory = AppConfig.load(), LangMemBackendConfig.from_env()
    assert (app.openai_api_key, app.openai_base_url, app.model_name) == (
        memory.openai_api_key,
        memory.openai_base_url,
        memory.model_name,
    )
    assert connection_guard_from_env().base_url == app.openai_base_url
