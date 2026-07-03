class BaseAgent:
    """Base class for JARVIS sub-agents."""
    def __init__(self, name: str):
        self.name = name

    async def run(self, task: str) -> str:
        raise NotImplementedError("Subclasses must implement run()")
