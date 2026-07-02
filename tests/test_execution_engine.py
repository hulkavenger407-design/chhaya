"""
Tests for Chhaya Execution Engine.
"""

from unittest.mock import MagicMock
import pytest

from chhaya.core.execution_engine import ExecutionEngine
from chhaya.domain.models import AgentBlueprint, ModelTier, GuardrailLevel, MemoryConfig
from chhaya.interfaces.event_bus import EventBus
from chhaya.interfaces.llm_provider import LLMProvider
from chhaya.interfaces.tool_plugin import ToolPlugin
from chhaya.core.tool_registry import ToolRegistry
from chhaya.interfaces.workspace import Workspace
from chhaya.interfaces.memory_provider import MemoryProvider, MemoryRecord


# --- Mock Implementations ---

class MockLLMProvider(LLMProvider):
    def __init__(self, expected_response="Mocked response", should_fail=False):
        self.expected_response = expected_response
        self.should_fail = should_fail
        self.last_prompt = None

    def generate(self, prompt: str, model_tier: str, **kwargs) -> str:
        self.last_prompt = prompt
        if self.should_fail:
            raise ValueError("LLM Failure")
        return self.expected_response


class MockEventBus(EventBus):
    def __init__(self):
        self.published_events = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.published_events.append({"type": event_type, "payload": payload})

    def subscribe(self, event_type: str, handler) -> None:
        pass


class MockTool(ToolPlugin):
    @property
    def name(self): return "mock_tool"
    @property
    def description(self): return "A mock tool for testing."
    def execute(self, **kwargs): return "Executed"


class MockWorkspace(Workspace):
    @property
    def base_path(self): return "/tmp/mock"
    def write_file(self, filename: str, content: str): pass
    def read_file(self, filename: str) -> str: return ""


class MockMemoryProvider(MemoryProvider):
    def __init__(self, mock_records=None):
        self.mock_records = mock_records or []

    def store(self, namespace: str, record: MemoryRecord) -> None:
        pass

    def search(self, namespace: str, query: str, limit: int = 5) -> list[MemoryRecord]:
        return self.mock_records

    def delete(self, namespace: str, record_id: str) -> bool:
        return True


# --- Tests ---

@pytest.fixture
def base_blueprint():
    return AgentBlueprint(
        name="test_agent",
        role="tester",
        system_prompt="You are testing.",
        model_tier=ModelTier.EXECUTION_7B,
        guardrail_level=GuardrailLevel.STRICT,
        tools=["mock_tool"]
    )


def test_execution_engine_success(base_blueprint):
    # Setup dependencies
    llm = MockLLMProvider(expected_response="Task complete!")
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory
    )

    # Run
    result = engine.run(blueprint=base_blueprint, task="Do the thing", workspace=workspace)

    # Assertions
    assert result == "Task complete!"

    # Check LLM Prompt construction
    assert "Role: tester" in llm.last_prompt
    assert "mock_tool: A mock tool for testing." in llm.last_prompt
    assert "Guardrail Level: STRICT" in llm.last_prompt
    assert "Do the thing" in llm.last_prompt

    # Check Events
    assert len(bus.published_events) == 2
    assert bus.published_events[0]["type"] == "agent_run_started"
    assert bus.published_events[1]["type"] == "agent_run_completed"
    assert bus.published_events[1]["payload"]["status"] == "success"
    assert bus.published_events[1]["payload"]["result"] == "Task complete!"


def test_execution_engine_failure(base_blueprint):
    llm = MockLLMProvider(should_fail=True)
    bus = MockEventBus()
    registry = ToolRegistry()
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory
    )

    with pytest.raises(RuntimeError, match="Execution failed for agent test_agent: LLM Failure"):
        engine.run(blueprint=base_blueprint, task="Do the thing", workspace=workspace)

    assert len(bus.published_events) == 2
    assert bus.published_events[0]["type"] == "agent_run_started"
    assert bus.published_events[1]["type"] == "agent_run_failed"
    assert "error" in bus.published_events[1]["payload"]


def test_execution_engine_with_memory_rag(base_blueprint):
    base_blueprint.memory_config.enable_vector_store = True

    llm = MockLLMProvider(expected_response="RAG complete!")
    bus = MockEventBus()
    registry = ToolRegistry()
    workspace = MockWorkspace()

    mock_records = [
        MemoryRecord(id="1", text="Past memory: user likes pizza"),
        MemoryRecord(id="2", text="Past memory: project name is Chhaya")
    ]
    memory = MockMemoryProvider(mock_records=mock_records)

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory
    )

    engine.run(blueprint=base_blueprint, task="What is the project name?", workspace=workspace)

    # Check LLM Prompt construction for RAG injection
    assert "Relevant Past Memories:" in llm.last_prompt
    assert "Past memory: user likes pizza" in llm.last_prompt
    assert "Past memory: project name is Chhaya" in llm.last_prompt
