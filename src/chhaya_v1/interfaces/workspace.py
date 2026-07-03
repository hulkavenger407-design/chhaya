"""
Workspace Interface for Chhaya.
Provides an abstraction for an isolated working environment for an agent.
"""

from abc import ABC, abstractmethod


class Workspace(ABC):
    """
    Abstract Base Class for an Agent Workspace.
    Defines the isolated environment where an agent can read/write files and execute tasks safely.
    """

    @property
    @abstractmethod
    def base_path(self) -> str:
        """
        Returns the physical or virtual root path of this workspace.
        """
        pass

    @abstractmethod
    def write_file(self, filename: str, content: str) -> None:
        """
        Writes content to a file inside the workspace.

        Args:
            filename (str): The name/path of the file relative to the workspace root.
            content (str): The content to write.
        """
        pass

    @abstractmethod
    def read_file(self, filename: str) -> str:
        """
        Reads content from a file inside the workspace.

        Args:
            filename (str): The name/path of the file relative to the workspace root.

        Returns:
            str: The content of the file.
        """
        pass
