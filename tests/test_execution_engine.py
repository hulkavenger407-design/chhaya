"""
Tests for Chhaya Execution Engine.
"""

from unittest.mock import MagicMock
import pytest

from chhaya_v1.core.execution_engine import ExecutionEngine
from chhaya_v1.domain.models import AgentBlueprint, ModelTier, GuardrailLevel, MemoryConfig
from chhaya_v1.interfaces.event_bus import EventBus
from chhaya_v1.interfaces.llm_provider import LLMProvider
from chhaya_v1.interfaces.tool_plugin import ToolPlugin
from chhaya_v1.core.tool_registry import ToolRegistry
from chhaya_v1.interfaces.workspace import Workspace
from chhaya_v1.interfaces.memory_provider import MemoryProvider, MemoryRecord


# --- Mock Implementations ---

class MockLLMProvider(LLMProvider):
    def __init__(self, responses, should_fail=False):
        self.responses = responses
        self.call_count = 0
        self.should_fail = should_fail
        self.last_prompt = None

    def generate(self, prompt: str, model_tier: str, **kwargs) -> str:
        self.last_prompt = prompt
        if self.should_fail:
            raise ValueError("LLM Failure")

        # Return sequence of responses for ReAct loop testing
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


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
    def execute(self, **kwargs): return "Executed the mock tool"


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
    llm = MockLLMProvider(responses=["Task complete!"])
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    # Pass an always-approve callback to bypass strict guardrails for the pure success test
    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory,
        approval_callback=lambda a, t, kwargs: True
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
    llm = MockLLMProvider(responses=[], should_fail=True)
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

    llm = MockLLMProvider(responses=["RAG complete!"])
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


def test_execution_engine_react_loop(base_blueprint):
    # LLM simulates a tool call, then a final answer
    responses = [
        '```json\n{"tool_call": true, "name": "mock_tool", "arguments": {}}\n```',
        'Final answer: The tool was executed.'
    ]

    llm = MockLLMProvider(responses=responses)
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory,
        approval_callback=lambda a, t, kwargs: True
    )

    result = engine.run(blueprint=base_blueprint, task="Use the tool", workspace=workspace)

    assert result == "Final answer: The tool was executed."
    assert llm.call_count == 2

    # Check that the observation was injected into the prompt
    assert "Observation: Executed the mock tool" in llm.last_prompt


def test_execution_engine_max_iterations(base_blueprint):
    # Simulate LLM stuck in an infinite tool call loop
    responses = ['```json\n{"tool_call": true, "name": "mock_tool", "arguments": {}}\n```'] * 15

    llm = MockLLMProvider(responses=responses)
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory,
        approval_callback=lambda a, t, kwargs: True
    )

    # Engine defaults to MAX_ITERATIONS = 10
    with pytest.raises(RuntimeError, match="exceeded maximum iterations"):
        engine.run(blueprint=base_blueprint, task="Loop forever", workspace=workspace)

    assert llm.call_count == 10


def test_execution_engine_guardrail_denied(base_blueprint):
    """Test that a denied tool call returns a failure observation to the LLM."""
    responses = [
        '```json\n{"tool_call": true, "name": "mock_tool", "arguments": {}}\n```',
        'Final answer: I was denied.'
    ]

    llm = MockLLMProvider(responses=responses)
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    # Reject all calls
    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory,
        approval_callback=lambda a, t, kwargs: False
    )

    result = engine.run(blueprint=base_blueprint, task="Use the tool", workspace=workspace)

    assert result == "Final answer: I was denied."
    # Check that the denial observation was injected
    assert "Observation: Error: Execution denied by user/guardrails." in llm.last_prompt


def test_execution_engine_guardrail_relaxed(base_blueprint):
    """Test that RELAXED guardrail automatically approves without the callback."""
    base_blueprint.guardrail_level = GuardrailLevel.RELAXED

    responses = [
        '```json\n{"tool_call": true, "name": "mock_tool", "arguments": {}}\n```',
        'Final answer: Done.'
    ]

    llm = MockLLMProvider(responses=responses)
    bus = MockEventBus()
    registry = ToolRegistry()
    registry.register(MockTool())
    workspace = MockWorkspace()
    memory = MockMemoryProvider()

    # Callback raises an error if called, proving it's bypassed
    def crash_callback(a, t, kwargs):
        raise AssertionError("Callback should not be invoked for RELAXED")

    engine = ExecutionEngine(
        llm_provider=llm,
        event_bus=bus,
        tool_registry=registry,
        memory_provider=memory,
        approval_callback=crash_callback
    )

    result = engine.run(blueprint=base_blueprint, task="Use the tool", workspace=workspace)
    assert result == "Final answer: Done."
