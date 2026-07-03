import httpx
from pydantic import BaseModel
from chhaya_v2.core.engine.config import settings

class ModelInfo(BaseModel):
    name: str
    size: str
    family: str

class OllamaRegistry:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.models: list[ModelInfo] = []

    async def discover(self) -> list[ModelInfo]:
        """Auto-discover models from Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                self.models = [
                    ModelInfo(name=m["name"], size=m["details"].get("parameter_size", "unknown"), family=m["details"].get("family", "unknown"))
                    for m in data.get("models", [])
                ]
                return self.models
        except Exception:
            return []
