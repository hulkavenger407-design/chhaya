"""
Execution Engine for Chhaya.
Orchestrates the running of an AgentBlueprint against a specific task.
"""

from typing import Any, Dict
import structlog

from chhaya.domain.models import AgentBlueprint
from chhaya.interfaces.event_bus import EventBus
from chhaya.interfaces.llm_provider import LLMProvider
from chhaya.core.tool_registry import ToolRegistry
from chhaya.interfaces.workspace import Workspace

logger = structlog.get_logger(__name__)


class ExecutionEngine:
    """
    Executes an agent run by coordinating the LLM, tools, and workspace.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
    ):
        """
        Initializes the Execution Engine with its required dependencies.
        """
        self.llm_provider = llm_provider
        self.event_bus = event_bus
        self.tool_registry = tool_registry

    def _build_system_prompt(self, blueprint: AgentBlueprint) -> str:
        """
        Constructs the final system prompt by combining the blueprint's core prompt
        with tool descriptions and guardrail instructions.
        """
        prompt = f"Role: {blueprint.role}\n\n{blueprint.system_prompt}\n\n"

        # Inject tool information
        if blueprint.tools:
            prompt += "You have access to the following tools:\n"
            for tool_name in blueprint.tools:
                tool = self.tool_registry.get_tool(tool_name)
                if tool:
                    prompt += f"- {tool.name}: {tool.description}\n"
                else:
                    logger.warning("Agent requested unregistered tool", tool=tool_name, agent=blueprint.name)

        # Inject guardrail instructions
        prompt += f"\nGuardrail Level: {blueprint.guardrail_level.value.upper()}\n"
        if blueprint.guardrail_level.value == "strict":
            prompt += "You MUST ask for user approval before making any external changes or API calls.\n"

        return prompt

    def run(self, blueprint: AgentBlueprint, task: str, workspace: Workspace) -> str:
        """
        Executes a single run loop for the agent to accomplish the task.

        Args:
            blueprint: The agent configuration.
            task: The user's input task.
            workspace: The isolated environment for this specific run.

        Returns:
            The final response string from the agent.
        """
        run_id = f"{blueprint.name}_{hash(task)}"

        logger.info("Starting agent run", agent=blueprint.name, task=task)
        self.event_bus.publish("agent_run_started", {
            "agent_name": blueprint.name,
            "task": task,
            "run_id": run_id
        })

        system_prompt = self._build_system_prompt(blueprint)

        # Construct the full prompt (in a real system, this would be a message array)
        # For Phase 4, we use a simple concatenated string representation.
        full_prompt = f"System:\n{system_prompt}\n\nUser Task:\n{task}\n\nAgent:"

        try:
            # Generate the response
            response = self.llm_provider.generate(
                prompt=full_prompt,
                model_tier=blueprint.model_tier.value
            )

            # (Phase 4 scope limitation: Tool parsing/execution loop will be built in subsequent phases.
            # Currently, it just performs a single LLM pass and returns).

            self.event_bus.publish("agent_run_completed", {
                "agent_name": blueprint.name,
                "run_id": run_id,
                "status": "success",
                "result": response
            })

            return response

        except Exception as e:
            logger.error("Agent run failed", agent=blueprint.name, error=str(e))
            self.event_bus.publish("agent_run_failed", {
                "agent_name": blueprint.name,
                "run_id": run_id,
                "error": str(e)
            })
            raise RuntimeError(f"Execution failed for agent {blueprint.name}: {e}") from e
