"""
Tool Plugin Interface for Chhaya.
Provides an abstraction for extending agent capabilities with custom tools.
"""

from abc import ABC, abstractmethod
from typing import Any


class ToolPlugin(ABC):
    """
    Abstract Base Class for a Tool Plugin.
    Every custom tool should implement this interface so it can be dynamically loaded.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the unique name of the tool.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Returns the description of what the tool does, used by the LLM to decide when to call it.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Executes the tool's core logic with the provided arguments.

        Args:
            **kwargs (Any): Arguments required by the tool.

        Returns:
            Any: The result of the execution.
        """
        pass
