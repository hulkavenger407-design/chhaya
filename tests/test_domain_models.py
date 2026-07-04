"""
Tests for Chhaya Domain Models.
"""

import pytest
from pydantic import ValidationError

from chhaya.domain.models import AgentBlueprint, ModelTier, GuardrailLevel, MemoryConfig


def test_agent_blueprint_valid_creation():
    """Test creating a valid AgentBlueprint with all standard fields."""
    blueprint = AgentBlueprint(
        name="TestAgent",
        role="A test agent",
        system_prompt="You are a helpful test agent.",
        model_tier=ModelTier.REASONING_14B,
        tools=["search_tool", "calculator_tool"],
        guardrail_level=GuardrailLevel.MODERATE
    )

    assert blueprint.name == "TestAgent"
    assert blueprint.role == "A test agent"
    assert blueprint.system_prompt == "You are a helpful test agent."
    assert blueprint.model_tier == ModelTier.REASONING_14B
    assert len(blueprint.tools) == 2
    assert blueprint.guardrail_level == GuardrailLevel.MODERATE
    assert blueprint.version == 1  # default

    # Defaults for memory config
    assert blueprint.memory_config.enable_scratchpad is True
    assert blueprint.memory_config.enable_vector_store is False


def test_agent_blueprint_defaults():
    """Test AgentBlueprint initialization with minimal required fields."""
    blueprint = AgentBlueprint(
        name="MinimalAgent",
        role="Minimal role",
        system_prompt="Minimal prompt"
    )

    assert blueprint.model_tier == ModelTier.EXECUTION_7B
    assert blueprint.guardrail_level == GuardrailLevel.STRICT
    assert blueprint.tools == []


def test_agent_blueprint_invalid_tier():
    """Test that invalid model tiers raise a ValidationError."""
    with pytest.raises(ValidationError):
        AgentBlueprint(
            name="BadTierAgent",
            role="role",
            system_prompt="prompt",
            model_tier="invalid_tier" # type: ignore
        )
