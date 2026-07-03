"""
Tests for Chhaya Configuration Loader.
"""

import os
import tempfile
import pytest

from chhaya_v1.core.config import load_config, ChhayaSettings


def test_load_config_defaults():
    """Test that configuration loads defaults when no file or env vars are present."""
    # Using a non-existent path to ensure defaults are used
    settings = load_config(config_path="/path/does/not/exist.yaml")

    assert settings.llm.default_provider == "ollama"
    assert settings.llm.tier_14b_model == "llama3:14b"
    assert settings.storage.backend == "sqlite"
    assert settings.ollama_base_url == "http://localhost:11434"


def test_load_config_from_yaml():
    """Test loading configuration from a provided YAML file."""
    yaml_content = """
llm:
  default_provider: "openai"
  tier_14b_model: "gpt-4-turbo"

storage:
  backend: "postgres"
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        settings = load_config(config_path=temp_path)

        assert settings.llm.default_provider == "openai"
        assert settings.llm.tier_14b_model == "gpt-4-turbo"
        assert settings.llm.tier_7b_model == "llama3:7b" # Should still be default
        assert settings.storage.backend == "postgres"
    finally:
        os.unlink(temp_path)


def test_load_config_env_overrides(monkeypatch):
    """Test that environment variables override both defaults and YAML."""
    # Setup mock env vars
    monkeypatch.setenv("CHHAYA_LLM__DEFAULT_PROVIDER", "anthropic")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://remote-ollama:11434")

    yaml_content = """
llm:
  default_provider: "openai"
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        settings = load_config(config_path=temp_path)

        # Env var should override the YAML value
        assert settings.llm.default_provider == "anthropic"
        # Env var should override the default
        assert settings.ollama_base_url == "http://remote-ollama:11434"
    finally:
        os.unlink(temp_path)
