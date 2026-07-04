"""
Tests for Chhaya Tool Registry.
"""

from typing import Any
import pytest

from chhaya.interfaces.tool_plugin import ToolPlugin
from chhaya.core.tool_registry import ToolRegistry


class DummyTool(ToolPlugin):
    def __init__(self, name: str, description: str = "A dummy tool"):
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, **kwargs: Any) -> Any:
        return f"Executed {self._name}"


def test_tool_registry_register_and_get():
    registry = ToolRegistry()
    tool = DummyTool(name="calculator")

    # Should not exist initially
    assert registry.get_tool("calculator") is None

    # Register and verify
    registry.register(tool)
    fetched_tool = registry.get_tool("calculator")

    assert fetched_tool is not None
    assert fetched_tool.name == "calculator"
    assert fetched_tool.execute() == "Executed calculator"


def test_tool_registry_duplicate_registration_fails():
    registry = ToolRegistry()
    tool1 = DummyTool(name="search")
    tool2 = DummyTool(name="search", description="Different description")

    registry.register(tool1)

    with pytest.raises(ValueError, match="is already registered"):
        registry.register(tool2)


def test_tool_registry_get_all_tools():
    registry = ToolRegistry()

    registry.register(DummyTool(name="tool1"))
    registry.register(DummyTool(name="tool2"))

    all_tools = registry.get_all_tools()
    assert len(all_tools) == 2

    names = [t.name for t in all_tools]
    assert "tool1" in names
    assert "tool2" in names


def test_tool_registry_unregister():
    registry = ToolRegistry()
    registry.register(DummyTool(name="temp_tool"))

    assert registry.get_tool("temp_tool") is not None

    # Unregister existing
    assert registry.unregister("temp_tool") is True
    assert registry.get_tool("temp_tool") is None

    # Unregister non-existing
    assert registry.unregister("non_existent") is False
