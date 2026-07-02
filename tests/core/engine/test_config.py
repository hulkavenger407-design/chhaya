import pytest
from pydantic import ValidationError
from chhaya.core.engine.config import Settings

def test_config_defaults():
    settings = Settings()
    assert settings.environment == "development"
    assert settings.default_chat_model == "phi3.5"

def test_config_override_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEFAULT_CHAT_MODEL", "llama3")

    settings = Settings()
    assert settings.environment == "production"
    assert settings.default_chat_model == "llama3"
