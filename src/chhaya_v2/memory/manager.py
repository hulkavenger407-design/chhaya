from chhaya_v2.memory.stores.short_term import ShortTermMemory
from chhaya_v2.memory.stores.episodic import EpisodicMemory
from chhaya_v2.core.graph.state import Message

class MemoryManager:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.episodic = EpisodicMemory()

    def add_message(self, message: Message):
        self.short_term.add(message)

    def get_context(self) -> str:
        recent = self.short_term.get_all()
        episodes = self.episodic.retrieve(limit=3)

        context = "Recent conversation:\n"
        for m in recent:
            context += f"{m.role}: {m.content}\n"

        if episodes:
            context += "\nRelevant past episodes:\n"
            for ep in episodes:
                context += f"- {ep}\n"

        return context
