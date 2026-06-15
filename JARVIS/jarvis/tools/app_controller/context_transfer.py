"""
jarvis/tools/app_controller/context_transfer.py

Carries conversation context when switching between AIs.
When Claude hits its limit and we switch to ChatGPT, we inject
a concise summary of the previous conversation so the new AI
has full context and doesn't start blind.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
import time


@dataclass
class ConversationTurn:
    role: str        # "user" or "ai"
    content: str
    ai_name: str
    timestamp: float = field(default_factory=time.time)


class ContextTransfer:
    """
    Maintains a rolling conversation buffer that can be
    injected as a preamble when switching AIs.
    """

    MAX_TURNS = 10  # last 10 exchanges to carry over

    def __init__(self):
        self.turns: List[ConversationTurn] = []
        self.current_topic: str = ""
        self.current_task_type: str = ""

    def add_turn(self, role: str, content: str, ai_name: str):
        self.turns.append(ConversationTurn(role, content, ai_name))
        if len(self.turns) > self.MAX_TURNS * 2:
            self.turns = self.turns[-self.MAX_TURNS * 2:]

    def set_topic(self, topic: str, task_type: str):
        self.current_topic = topic
        self.current_task_type = task_type

    def build_handoff_prompt(self, from_ai: str, to_ai: str) -> str:
        """
        Build a prompt that introduces context to the new AI.
        This is prepended to the next message so the new AI
        understands what we were working on.
        """
        if not self.turns:
            return ""

        lines = [
            f"[CONTEXT HANDOFF: Continuing from {from_ai} to {to_ai}]",
            f"Task type: {self.current_task_type}",
            f"Topic: {self.current_topic}",
            "",
            "Previous conversation summary:",
        ]

        # Last few turns for context
        recent = self.turns[-6:]
        for turn in recent:
            prefix = "User" if turn.role == "user" else f"AI ({turn.ai_name})"
            # Truncate very long messages
            content = turn.content[:300] + "..." if len(turn.content) > 300 else turn.content
            lines.append(f"  {prefix}: {content}")

        lines.append("")
        lines.append("Continue from where we left off:")
        return "\n".join(lines)

    def clear(self):
        self.turns.clear()
        self.current_topic = ""
        self.current_task_type = ""

    def summarize_for_memory(self) -> str:
        """Create a short summary of this session for long-term memory."""
        if not self.turns:
            return ""
        user_messages = [t.content for t in self.turns if t.role == "user"]
        ais_used = list(dict.fromkeys(t.ai_name for t in self.turns))
        return (
            f"Session: {self.current_topic or 'General conversation'} | "
            f"Task: {self.current_task_type} | "
            f"AIs used: {', '.join(ais_used)} | "
            f"Exchanges: {len(user_messages)}"
        )


# Singleton
_context = None

def get_context_transfer() -> ContextTransfer:
    global _context
    if _context is None:
        _context = ContextTransfer()
    return _context
