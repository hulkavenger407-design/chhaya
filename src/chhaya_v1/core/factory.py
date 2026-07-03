"""
Factory Engine for Chhaya.
Uses the Reasoning LLM to design new AgentBlueprints based on natural language briefs.
"""

import json
from typing import Any, Dict
import structlog

from chhaya_v1.domain.models import AgentBlueprint, ModelTier, GuardrailLevel, MemoryConfig
from chhaya_v1.interfaces.llm_provider import LLMProvider
from chhaya_v1.core.agent_registry import AgentRegistry
from chhaya_v1.core.tool_registry import ToolRegistry
from chhaya_v1.interfaces.event_bus import EventBus

logger = structlog.get_logger(__name__)


class AgentFactory:
    """
    Creates and registers new AgentBlueprints based on user prompts.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
    ):
        self.llm = llm_provider
        self.registry = agent_registry
        self.tools = tool_registry
        self.event_bus = event_bus

    def _build_design_prompt(self, brief: str) -> str:
        """
        Constructs the prompt for the 14b reasoning model to output a valid JSON blueprint.
        """
        available_tools = [tool.name for tool in self.tools.get_all_tools()]

        prompt = f"""You are the Chhaya Agent Factory. Your job is to design a specialized AI Agent based on the user's brief.

Available tools you can assign to this agent: {available_tools}
Available model tiers: '14b' (complex reasoning), '7b' (fast execution)
Available guardrail levels: 'strict', 'moderate', 'relaxed'

User Brief:
"{brief}"

Design the agent and output ONLY a raw JSON object matching this schema perfectly (do not use markdown blocks like ```json):
{{
    "name": "lowercase_underscore_name",
    "role": "Short description of the agent's role",
    "system_prompt": "The detailed system prompt and instructions for the agent to follow.",
    "model_tier": "14b" or "7b",
    "tools": ["tool_name_1", "tool_name_2"],
    "guardrail_level": "strict",
    "memory_config": {{
        "enable_scratchpad": true,
        "enable_vector_store": false,
        "shared_memory_access": false
    }}
}}
"""
        return prompt

    def create_agent(self, brief: str) -> AgentBlueprint:
        """
        Designs a new agent using the LLM and saves it to the registry.

        Args:
            brief: The natural language description of what the agent should do.

        Returns:
            The newly created and saved AgentBlueprint.
        """
        logger.info("Factory starting agent design", brief=brief)

        self.event_bus.publish("factory_design_started", {"brief": brief})

        prompt = self._build_design_prompt(brief)

        try:
            # Force the reasoning model tier (14b) for design tasks
            # Ask the provider for JSON format if supported (like in Ollama)
            response_text = self.llm.generate(
                prompt=prompt,
                model_tier=ModelTier.REASONING_14B.value,
                format="json"
            )

            # Clean up the response in case the LLM ignored instructions and wrapped it in markdown
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.strip("`").removeprefix("json").strip()

            design_data: Dict[str, Any] = json.loads(response_text)

            blueprint = AgentBlueprint(**design_data)

            # Save it
            self.registry.save_blueprint(blueprint)

            self.event_bus.publish("factory_design_completed", {
                "agent_name": blueprint.name,
                "role": blueprint.role
            })

            logger.info("Factory successfully created agent", agent_name=blueprint.name)
            return blueprint

        except json.JSONDecodeError as e:
            logger.error("Factory failed to parse LLM JSON output", error=str(e), response=response_text)
            self.event_bus.publish("factory_design_failed", {"error": "Invalid JSON generated"})
            raise ValueError(f"Failed to generate valid agent design: {e}") from e

        except Exception as e:
            logger.error("Factory encountered an error", error=str(e))
            self.event_bus.publish("factory_design_failed", {"error": str(e)})
            raise
