"""
Built-in Memory Tool for Chhaya Agents.
Allows agents to save semantic facts into their long-term memory.
"""

from typing import Any
import uuid
import structlog

from chhaya_v1.interfaces.tool_plugin import ToolPlugin
from chhaya_v1.interfaces.memory_provider import MemoryProvider, MemoryRecord

logger = structlog.get_logger(__name__)


class SaveMemoryTool(ToolPlugin):
    """
    A built-in tool that allows an agent to persist a fact to their vector store.
    """

    def __init__(self, memory_provider: MemoryProvider):
        self.memory_provider = memory_provider

    @property
    def name(self) -> str:
        return "save_memory"

    @property
    def description(self) -> str:
        return "Saves an important fact or piece of information to your long-term memory. Arguments required: 'fact' (string)."

    def execute(self, **kwargs: Any) -> Any:
        agent_name = kwargs.get("_agent_name")
        fact = kwargs.get("fact")

        if not agent_name:
            return "Error: Internal execution missing _agent_name context."

        if not fact:
            return "Error: You must provide a 'fact' string to save."

        try:
            record_id = str(uuid.uuid4())
            record = MemoryRecord(id=record_id, text=fact, metadata={"source": "agent_self_reflection"})
            self.memory_provider.store(namespace=agent_name, record=record)

            logger.info("Agent saved memory", agent=agent_name, memory_id=record_id)
            return f"Successfully saved fact to long-term memory. ID: {record_id}"
        except Exception as e:
            logger.error("Agent failed to save memory", agent=agent_name, error=str(e))
            return f"Failed to save memory due to internal error: {e}"
