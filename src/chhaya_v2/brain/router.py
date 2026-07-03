from chhaya_v2.core.engine.config import settings

class TaskRouter:
    def route(self, user_input: str) -> str:
        """Basic task-to-model routing."""
        lower_input = user_input.lower()
        if "code" in lower_input or "python" in lower_input or "function" in lower_input:
            return settings.default_code_model
        return settings.default_chat_model
