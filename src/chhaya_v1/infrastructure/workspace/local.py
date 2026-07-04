"""
Local Workspace Implementation.
Provides an isolated file system environment for an agent.
"""

import os
from pathlib import Path
import structlog

from chhaya.interfaces.workspace import Workspace
from chhaya.core.config import settings

logger = structlog.get_logger(__name__)


class LocalWorkspace(Workspace):
    """
    Concrete implementation of Workspace that uses a local directory.
    Prevents path traversal attacks to ensure agents cannot escape their isolated directory.
    """

    def __init__(self, agent_name: str, base_path: str | None = None) -> None:
        """
        Initializes the Local Workspace for a specific agent.

        Args:
            agent_name: The name of the agent (used to create a subdirectory).
            base_path: The root directory for all workspaces. Defaults to config settings.
        """
        root_path = Path(base_path or settings.workspace.base_path)
        self._base_path = (root_path / agent_name).resolve()

        # Create the directory if it doesn't exist
        os.makedirs(self._base_path, exist_ok=True)
        logger.info("Initialized Local Workspace", path=str(self._base_path), agent=agent_name)

    @property
    def base_path(self) -> str:
        return str(self._base_path)

    def _get_safe_path(self, filename: str) -> Path:
        """
        Resolves the filename and ensures it strictly resides within the base_path.

        Raises:
            ValueError: If a path traversal is detected.
        """
        requested_path = (self._base_path / filename).resolve()

        # Ensure the resolved path starts with the base_path
        if not requested_path.is_relative_to(self._base_path):
            logger.warning("Path traversal attempt detected", requested_file=filename)
            raise ValueError(f"Access denied: {filename} is outside the workspace.")

        return requested_path

    def write_file(self, filename: str, content: str) -> None:
        """
        Writes content to a file safely inside the workspace.
        """
        safe_path = self._get_safe_path(filename)

        # Ensure parent directories exist (e.g., if filename is "src/main.py")
        os.makedirs(safe_path.parent, exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug("Wrote file in workspace", filename=filename)

    def read_file(self, filename: str) -> str:
        """
        Reads content from a file safely inside the workspace.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        safe_path = self._get_safe_path(filename)

        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"File not found in workspace: {filename}")

        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.debug("Read file in workspace", filename=filename)
        return content
