"""
Domain Models for Chhaya.
Defines the core data structures used throughout the system.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    """
    Available model tiers for an agent.
    14b: Complex reasoning, planning, self-improvement.
    7b: Fast, cheap, high-volume execution.
    """
    REASONING_14B = "14b"
    EXECUTION_7B = "7b"


class GuardrailLevel(str, Enum):
    """
    Guardrail strictness for an agent's autonomy.
    """
    STRICT = "strict"   # Requires approval for all external actions.
    MODERATE = "moderate" # Requires approval for spending/destructive actions.
    RELAXED = "relaxed"  # Fully autonomous, logs only.


class MemoryConfig(BaseModel):
    """
    Configuration for an agent's memory capabilities.
    """
    enable_scratchpad: bool = Field(default=True, description="Use short-term scratchpad memory.")
    enable_vector_store: bool = Field(default=False, description="Use long-term vector memory.")
    shared_memory_access: bool = Field(default=False, description="Can access the shared Chhaya-level memory.")


class AgentBlueprint(BaseModel):
    """
    The fundamental data structure defining a Chhaya agent.
    Never hardcoded logic, entirely data-driven.
    """
    name: str = Field(..., description="The unique name of the agent.")
    role: str = Field(..., description="A short description of the agent's purpose.")
    system_prompt: str = Field(..., description="The core instruction set for the LLM.")

    model_tier: ModelTier = Field(
        default=ModelTier.EXECUTION_7B,
        description="The LLM tier to use (14b or 7b)."
    )

    tools: List[str] = Field(
        default_factory=list,
        description="List of tool names this agent is authorized to use."
    )

    memory_config: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory configuration for the agent."
    )

    guardrail_level: GuardrailLevel = Field(
        default=GuardrailLevel.STRICT,
        description="The strictness of autonomy guardrails."
    )

    version: int = Field(
        default=1,
        description="The version number of this blueprint (auto-increments on reflection changes)."
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any additional arbitrary metadata for the agent."
    )
