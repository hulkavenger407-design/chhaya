"""
Ollama Provider Implementation.
Communicates with a local Ollama instance.
"""

from typing import Any
import httpx
import structlog

from chhaya.interfaces.llm_provider import LLMProvider
from chhaya.core.config import settings

logger = structlog.get_logger(__name__)


class OllamaProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider using Ollama.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """
        Initializes the Ollama Provider.

        Args:
            base_url: The URL of the Ollama instance. Defaults to the value in settings.
        """
        self.base_url = base_url or settings.ollama_base_url
        self.generate_endpoint = f"{self.base_url.rstrip('/')}/api/generate"

    def _get_model_name(self, model_tier: str) -> str:
        """Resolves a tier (e.g., '14b') to the actual model name in config."""
        if model_tier == "14b":
            return settings.llm.tier_14b_model
        elif model_tier == "7b":
            return settings.llm.tier_7b_model
        else:
            # Fallback to returning the tier string directly if it doesn't match standard tiers
            # (Allows direct model naming if necessary)
            return model_tier

    def generate(self, prompt: str, model_tier: str, **kwargs: Any) -> str:
        """
        Calls the Ollama /api/generate endpoint.
        """
        model_name = self._get_model_name(model_tier)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
        }

        # Merge any additional provider-specific parameters
        if kwargs:
            payload.update(kwargs)

        logger.info("Calling Ollama API", model=model_name, endpoint=self.generate_endpoint)

        try:
            with httpx.Client() as client:
                response = client.post(self.generate_endpoint, json=payload, timeout=120.0)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")

        except httpx.HTTPError as e:
            logger.error("Ollama API request failed", error=str(e))
            raise RuntimeError(f"Ollama generation failed: {e}") from e
