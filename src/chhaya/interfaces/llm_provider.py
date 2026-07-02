"""
LLM Provider Interface for Chhaya.
Provides abstractions for interacting with different Language Models (e.g., Ollama, OpenAI).
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Abstract Base Class for LLM interaction.
    Allows swapping out Ollama for other providers in the future.
    """

    @abstractmethod
    def generate(self, prompt: str, model_tier: str, **kwargs: Any) -> str:
        """
        Generates text based on a prompt and a designated model tier.

        Args:
            prompt (str): The input text to prompt the LLM.
            model_tier (str): The tier of the model to use (e.g., '14b', '7b').
            **kwargs (Any): Additional provider-specific parameters (e.g., temperature).

        Returns:
            str: The generated output text.
        """
        pass
