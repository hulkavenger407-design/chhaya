"""
Tests for Chhaya Reflection Engine.
"""

from typing import Any, Dict
import pytest

from chhaya_v1.core.reflection_engine import ReflectionEngine
from chhaya_v1.interfaces.llm_provider import LLMProvider
from chhaya_v1.core.agent_registry import AgentRegistry
from chhaya_v1.core.tool_registry import ToolRegistry
from chhaya_v1.interfaces.event_bus import EventBus
from chhaya_v1.domain.models import AgentBlueprint, ModelTier


class MockLLMProvider(LLMProvider):
    def __init__(self, json_response: str):
        self.json_response = json_response
        self.last_prompt = ""

    def generate(self, prompt: str, model_tier: str, **kwargs: Any) -> str:
        self.last_prompt = prompt
        return self.json_response


class MockAgentRegistry(AgentRegistry):
    def __init__(self):
        self.blueprints: Dict[str, AgentBlueprint] = {}

    def save_blueprint(self, blueprint: AgentBlueprint) -> None:
        self.blueprints[blueprint.name] = blueprint

    def load_blueprint(self, name: str) -> AgentBlueprint | None:
        return self.blueprints.get(name)


class MockEventBus(EventBus):
    def __init__(self):
        self.events = []

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))

    def subscribe(self, event_type: str, handler) -> None:
        pass


@pytest.fixture
def reflection_deps():
    registry = MockAgentRegistry()

    # Pre-load an agent to reflect upon
    original = AgentBlueprint(
        name="test_bot",
        role="tester",
        system_prompt="Do test.",
        version=1,
        tools=["basic_tool"]
    )
    registry.save_blueprint(original)

    tools = ToolRegistry()
    events = MockEventBus()
    return registry, tools, events


def test_reflection_engine_success(reflection_deps):
    registry, tools, events = reflection_deps

    json_response = '''
    {
        "system_prompt": "Do test, but do it better.",
        "tools": ["basic_tool", "advanced_tool"]
    }
    '''

    llm = MockLLMProvider(json_response=json_response)
    engine = ReflectionEngine(llm, registry, tools, events)

    new_blueprint = engine.reflect_and_improve(
        blueprint_name="test_bot",
        task="Test the thing.",
        result="I tested it, but failed.",
        feedback="You need to use the advanced tool."
    )

    # Check that version incremented
    assert new_blueprint.version == 2

    # Check that fields updated
    assert new_blueprint.system_prompt == "Do test, but do it better."
    assert "advanced_tool" in new_blueprint.tools

    # Check that immutable fields remained
    assert new_blueprint.name == "test_bot"
    assert new_blueprint.role == "tester"

    # Check that it was saved to registry
    loaded = registry.load_blueprint("test_bot")
    assert loaded.version == 2

    # Check events
    event_types = [e[0] for e in events.events]
    assert "reflection_started" in event_types
    assert "reflection_completed" in event_types


def test_reflection_engine_not_found(reflection_deps):
    registry, tools, events = reflection_deps
    llm = MockLLMProvider(json_response="{}")
    engine = ReflectionEngine(llm, registry, tools, events)

    with pytest.raises(ValueError, match="Cannot reflect on unknown agent"):
        engine.reflect_and_improve("ghost_bot", "task", "result", "feedback")


def test_reflection_engine_invalid_json(reflection_deps):
    registry, tools, events = reflection_deps
    llm = MockLLMProvider(json_response="I am not JSON")
    engine = ReflectionEngine(llm, registry, tools, events)

    with pytest.raises(ValueError, match="Failed to parse reflection updates"):
        engine.reflect_and_improve("test_bot", "task", "result", "feedback")

    event_types = [e[0] for e in events.events]
    assert "reflection_failed" in event_types
