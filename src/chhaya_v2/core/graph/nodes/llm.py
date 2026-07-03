from chhaya_v2.core.graph.state import JarvisState, Message
from chhaya_v2.core.engine.config import settings
import httpx

async def call_llm(state: JarvisState) -> dict:
    """Basic Ollama generation."""
    model = state.get("selected_model") or settings.default_chat_model
    messages = state["messages"]

    # We only use the last message for simplicity in this node,
    # normally we'd format all messages for Ollama API
    last_msg = messages[-1].content if messages else ""
    context = state.get("memory_context", "")

    prompt = f"Context:\n{context}\n\nUser: {last_msg}" if context else last_msg

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False}
            )
            response.raise_for_status()
            data = response.json()
            return {"messages": [Message(role="assistant", content=data["response"])]}
    except Exception as e:
        return {"messages": [Message(role="assistant", content=f"Error connecting to LLM: {e}")]}
