from chhaya_v2.core.agents.base_agent import BaseAgent

class CoordinatorAgent(BaseAgent):
    """Coordinates multiple sub-agents (Placeholder for Phase 1)."""
    def __init__(self):
        super().__init__("Coordinator")
        self.agents = []

    def register_agent(self, agent: BaseAgent):
        self.agents.append(agent)

    async def run(self, task: str) -> str:
        return f"Coordinating task: {task}"
