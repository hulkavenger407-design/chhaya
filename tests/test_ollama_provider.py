"""
Tests for Chhaya Ollama Provider.
"""

from unittest.mock import patch, MagicMock
import pytest
import httpx

from chhaya.infrastructure.llm.ollama import OllamaProvider
from chhaya.domain.models import ModelTier


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.Client.post") as mock_post:
        yield mock_post


def test_ollama_provider_init():
    """Test initialization with default and custom URLs."""
    provider1 = OllamaProvider()
    # Assuming the default config loaded in tests points to localhost
    assert "http://localhost:11434" in provider1.generate_endpoint

    provider2 = OllamaProvider(base_url="http://custom-ollama:8080")
    assert provider2.generate_endpoint == "http://custom-ollama:8080/api/generate"


def test_ollama_provider_generate_success(mock_httpx_post):
    """Test successful generation."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"model": "llama3:7b", "response": "Hello from Ollama!"}
    mock_response.raise_for_status.return_value = None
    mock_httpx_post.return_value = mock_response

    provider = OllamaProvider()
    result = provider.generate(prompt="Say hello", model_tier="7b", temperature=0.7)

    assert result == "Hello from Ollama!"

    # Verify the correct payload was sent
    mock_httpx_post.assert_called_once()
    call_kwargs = mock_httpx_post.call_args.kwargs
    assert call_kwargs["json"]["prompt"] == "Say hello"
    # It should resolve '7b' to the config value (e.g., llama3:7b)
    assert call_kwargs["json"]["model"] == "llama3:7b"
    assert call_kwargs["json"]["stream"] is False
    assert call_kwargs["json"]["temperature"] == 0.7


def test_ollama_provider_generate_http_error(mock_httpx_post):
    """Test generation failure raises appropriate error."""
    # Setup mock response to raise HTTPError
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=MagicMock()
    )
    mock_httpx_post.return_value = mock_response

    provider = OllamaProvider()

    with pytest.raises(RuntimeError, match="Ollama generation failed"):
        provider.generate(prompt="Trigger error", model_tier=ModelTier.REASONING_14B)
