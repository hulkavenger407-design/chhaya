"""
Tests for Chhaya Agent Factory.
"""

from typing import Any
import pytest

from chhaya.core.factory import AgentFactory
from chhaya.interfaces.llm_provider import LLMProvider
from chhaya.core.agent_registry import AgentRegistry
from chhaya.core.tool_registry import ToolRegistry
from chhaya.interfaces.event_bus import EventBus
from chhaya.interfaces.storage_provider import StorageProvider
from chhaya.domain.models import ModelTier, GuardrailLevel


class MockLLMProvider(LLMProvider):
    def __init__(self, json_response: str):
        self.json_response = json_response

    def generate(self, prompt: str, model_tier: str, **kwargs: Any) -> str:
        return self.json_response


class MockStorageProvider(StorageProvider):
    def save(self, collection: str, key: str, data: dict[str, Any]) -> None: pass
    def load(self, collection: str, key: str) -> dict[str, Any] | None: return None
    def list(self, collection: str) -> list[dict[str, Any]]: return []


class MockEventBus(EventBus):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: pass
    def subscribe(self, event_type: str, handler) -> None: pass


@pytest.fixture
def factory_deps():
    registry = AgentRegistry(storage_provider=MockStorageProvider())
    tools = ToolRegistry()
    events = MockEventBus()
    return registry, tools, events


def test_factory_create_agent_success(factory_deps):
    registry, tools, events = factory_deps

    valid_json = '''
    {
        "name": "data_analyzer",
        "role": "Analyzes CSV data",
        "system_prompt": "You are a data analyst.",
        "model_tier": "14b",
        "tools": [],
        "guardrail_level": "moderate",
        "memory_config": {
            "enable_scratchpad": true,
            "enable_vector_store": true,
            "shared_memory_access": false
        }
    }
    '''

    llm = MockLLMProvider(json_response=valid_json)
    factory = AgentFactory(llm_provider=llm, agent_registry=registry, tool_registry=tools, event_bus=events)

    blueprint = factory.create_agent("I need a data analyzer.")

    assert blueprint.name == "data_analyzer"
    assert blueprint.role == "Analyzes CSV data"
    assert blueprint.model_tier == ModelTier.REASONING_14B
    assert blueprint.guardrail_level == GuardrailLevel.MODERATE
    assert blueprint.memory_config.enable_vector_store is True


def test_factory_create_agent_cleans_markdown(factory_deps):
    registry, tools, events = factory_deps

    markdown_json = '''```json
    {
        "name": "markdown_agent",
        "role": "Testing markdown stripping",
        "system_prompt": "Prompt.",
        "model_tier": "7b",
        "tools": [],
        "guardrail_level": "relaxed",
        "memory_config": {
            "enable_scratchpad": false,
            "enable_vector_store": false,
            "shared_memory_access": false
        }
    }
    ```'''

    llm = MockLLMProvider(json_response=markdown_json)
    factory = AgentFactory(llm_provider=llm, agent_registry=registry, tool_registry=tools, event_bus=events)

    blueprint = factory.create_agent("Brief.")
    assert blueprint.name == "markdown_agent"


def test_factory_create_agent_invalid_json(factory_deps):
    registry, tools, events = factory_deps

    bad_json = 'This is not JSON.'

    llm = MockLLMProvider(json_response=bad_json)
    factory = AgentFactory(llm_provider=llm, agent_registry=registry, tool_registry=tools, event_bus=events)

    with pytest.raises(ValueError, match="Failed to generate valid agent design"):
        factory.create_agent("Brief.")
