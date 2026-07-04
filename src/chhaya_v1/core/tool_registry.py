"""
Tool Registry for Chhaya.
Manages the registration and discovery of ToolPlugins.
"""

from typing import Dict, List, Optional
import structlog

from chhaya.interfaces.tool_plugin import ToolPlugin

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Registry for managing available tools.
    Agents use this to look up tools they are authorized to use.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolPlugin] = {}
        logger.debug("Initialized empty Tool Registry")

    def register(self, tool: ToolPlugin) -> None:
        """
        Registers a new tool plugin.

        Args:
            tool: An instance of a class implementing ToolPlugin.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            logger.error("Attempted to register duplicate tool", tool_name=tool.name)
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")

        self._tools[tool.name] = tool
        logger.info("Registered tool", tool_name=tool.name)

    def get_tool(self, name: str) -> Optional[ToolPlugin]:
        """
        Fetches a registered tool by name.

        Args:
            name: The name of the tool to fetch.

        Returns:
            The ToolPlugin instance, or None if not found.
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolPlugin]:
        """
        Returns a list of all registered tools.
        """
        return list(self._tools.values())

    def unregister(self, name: str) -> bool:
        """
        Unregisters a tool by name.

        Args:
            name: The name of the tool to remove.

        Returns:
            True if the tool was removed, False if it wasn't found.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Unregistered tool", tool_name=name)
            return True
        return False
