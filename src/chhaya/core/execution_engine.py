"""
Execution Engine for Chhaya.
Orchestrates the running of an AgentBlueprint against a specific task.
"""

import json
from typing import Any, Callable, Dict, Optional
import structlog

from chhaya.domain.models import AgentBlueprint, GuardrailLevel
from chhaya.interfaces.event_bus import EventBus
from chhaya.interfaces.llm_provider import LLMProvider
from chhaya.core.tool_registry import ToolRegistry
from chhaya.interfaces.workspace import Workspace
from chhaya.interfaces.memory_provider import MemoryProvider

logger = structlog.get_logger(__name__)


class ExecutionEngine:
    """
    Executes an agent run by coordinating the LLM, tools, and workspace.
    """

    MAX_ITERATIONS = 10

    def __init__(
        self,
        llm_provider: LLMProvider,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        memory_provider: MemoryProvider,
        approval_callback: Optional[Callable[[str, str, Dict[str, Any]], bool]] = None
    ):
        """
        Initializes the Execution Engine with its required dependencies.

        Args:
            approval_callback: A function that takes (agent_name, tool_name, arguments)
                               and returns a boolean indicating if the tool execution is approved.
                               If None, actions requiring approval are automatically denied.
        """
        self.llm_provider = llm_provider
        self.event_bus = event_bus
        self.tool_registry = tool_registry
        self.memory_provider = memory_provider
        self.approval_callback = approval_callback

    def _build_system_prompt(self, blueprint: AgentBlueprint) -> str:
        """
        Constructs the final system prompt by combining the blueprint's core prompt
        with tool descriptions, guardrail instructions, and ReAct loop formatting.
        """
        prompt = f"Role: {blueprint.role}\n\n{blueprint.system_prompt}\n\n"

        # Inject ReAct format instructions
        prompt += """To interact with the user, simply reply directly with your text.
If you need to use a tool to gather information or perform an action, output ONLY a valid JSON object starting with ```json containing the key "tool_call", "name", and "arguments".
Example:
```json
{
  "tool_call": true,
  "name": "tool_name",
  "arguments": {"arg1": "value"}
}
```
The system will run the tool and feed the observation back to you. Do NOT output anything else when making a tool call.
\n"""

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
        if blueprint.guardrail_level == GuardrailLevel.STRICT:
            prompt += "You MUST ask for user approval before making any external changes or API calls. The system will intercept these for approval automatically.\n"

        return prompt

    def _parse_tool_call(self, llm_output: str) -> Dict[str, Any] | None:
        """
        Attempts to parse a tool call from the LLM output.
        """
        cleaned = llm_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()

        if cleaned.startswith("{") and "tool_call" in cleaned:
            try:
                data = json.loads(cleaned)
                if data.get("tool_call") is True and "name" in data:
                    return data
            except json.JSONDecodeError:
                pass
        return None

    def _check_guardrails(self, blueprint: AgentBlueprint, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Evaluates whether a tool call is permitted based on the agent's guardrail level.

        Returns True if approved, False if denied.
        """
        if blueprint.guardrail_level == GuardrailLevel.RELAXED:
            return True

        # For this slice, STRICT means ALL tool calls require human approval.
        # MODERATE could mean checking against a list of "safe" tools, but we'll treat it
        # as requiring approval for specific tools (simulated here as all tools except 'save_memory')
        needs_approval = False

        if blueprint.guardrail_level == GuardrailLevel.STRICT:
            needs_approval = True
        elif blueprint.guardrail_level == GuardrailLevel.MODERATE:
            # Hardcoded sensitive list for demonstration
            safe_tools = ["save_memory"]
            if tool_name not in safe_tools:
                needs_approval = True

        if not needs_approval:
            return True

        logger.info("Guardrail intercept: Approval required", agent=blueprint.name, tool=tool_name)
        self.event_bus.publish("guardrail_approval_requested", {
            "agent_name": blueprint.name,
            "tool_name": tool_name,
            "arguments": arguments
        })

        if self.approval_callback:
            approved = self.approval_callback(blueprint.name, tool_name, arguments)
            if approved:
                logger.info("Guardrail intercept: Approved", agent=blueprint.name, tool=tool_name)
                return True
            else:
                logger.info("Guardrail intercept: Denied", agent=blueprint.name, tool=tool_name)
                return False

        # If no callback is configured, deny by default for safety
        logger.warning("Guardrail intercept: Denied (No approval callback configured)", agent=blueprint.name)
        return False

    def run(self, blueprint: AgentBlueprint, task: str, workspace: Workspace) -> str:
        """
        Executes a ReAct loop for the agent to accomplish the task.
        """
        run_id = f"{blueprint.name}_{hash(task)}"

        logger.info("Starting agent run", agent=blueprint.name, task=task)
        self.event_bus.publish("agent_run_started", {
            "agent_name": blueprint.name,
            "task": task,
            "run_id": run_id
        })

        system_prompt = self._build_system_prompt(blueprint)

        # Integrate Memory (RAG)
        context_string = ""
        if blueprint.memory_config.enable_vector_store:
            try:
                memories = self.memory_provider.search(namespace=blueprint.name, query=task, limit=3)
                if memories:
                    context_string = "Relevant Past Memories:\n"
                    for m in memories:
                        context_string += f"- {m.text}\n"
                    context_string += "\n"
            except Exception as e:
                logger.warning("Failed to retrieve memories for agent run", agent=blueprint.name, error=str(e))

        # Start the conversation history
        history = f"System:\n{system_prompt}\n\n{context_string}User Task:\n{task}\n"

        try:
            iterations = 0
            while iterations < self.MAX_ITERATIONS:
                prompt_to_send = f"{history}\nAgent:"

                # Generate the response
                response = self.llm_provider.generate(
                    prompt=prompt_to_send,
                    model_tier=blueprint.model_tier.value
                )

                # Append agent's response to history
                history += f"\nAgent: {response}"

                # Check if the agent wants to call a tool
                tool_call = self._parse_tool_call(response)

                if tool_call:
                    tool_name = tool_call.get("name")
                    arguments = tool_call.get("arguments", {})

                    logger.debug("Attempting tool call", tool=tool_name, arguments=arguments)

                    # Ensure tool is authorized for this agent
                    if tool_name not in blueprint.tools:
                        observation = f"Error: Tool '{tool_name}' is not authorized for this agent."
                    else:
                        # Guardrail Check
                        if not self._check_guardrails(blueprint, tool_name, arguments):
                            observation = "Error: Execution denied by user/guardrails."
                        else:
                            tool = self.tool_registry.get_tool(tool_name)
                            if tool:
                                try:
                                    # Inject context dependencies to kwargs
                                    arguments["_agent_name"] = blueprint.name
                                    arguments["_workspace"] = workspace

                                    observation = str(tool.execute(**arguments))
                                except Exception as ex:
                                    observation = f"Tool execution failed: {ex}"
                            else:
                                observation = f"Error: Tool '{tool_name}' not found in registry."

                    logger.debug("Tool observation", tool=tool_name, observation=observation)
                    history += f"\nObservation: {observation}"
                    iterations += 1
                else:
                    # Final answer received
                    self.event_bus.publish("agent_run_completed", {
                        "agent_name": blueprint.name,
                        "run_id": run_id,
                        "status": "success",
                        "result": response
                    })
                    return response

            # Hit max iterations without final answer
            raise RuntimeError("Agent run exceeded maximum iterations without completing the task.")

        except Exception as e:
            logger.error("Agent run failed", agent=blueprint.name, error=str(e))
            self.event_bus.publish("agent_run_failed", {
                "agent_name": blueprint.name,
                "run_id": run_id,
                "error": str(e)
            })
            raise RuntimeError(f"Execution failed for agent {blueprint.name}: {e}") from e
