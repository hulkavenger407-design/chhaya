"""
Jules Integration Tool.
Allows local Chhaya agents to delegate highly complex tasks to a cloud-based highly-capable agent (Jules).
"""

from typing import Any
import httpx
import structlog
import socket

from chhaya_v1.interfaces.tool_plugin import ToolPlugin
from chhaya_v1.core.config import settings

logger = structlog.get_logger(__name__)


def is_connected() -> bool:
    """Check if the machine has active internet connectivity."""
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except OSError:
        pass
    return False


class AskJulesTool(ToolPlugin):
    """
    A built-in tool that allows an agent to request help from the cloud agent 'Jules'.
    """

    @property
    def name(self) -> str:
        return "ask_jules"

    @property
    def description(self) -> str:
        return "Delegates a highly complex task to a superior cloud-based agent named 'Jules'. Use this when a task requires deep internet research, complex coding beyond your abilities, or significant computational power. Arguments required: 'task' (string describing exactly what you need Jules to do)."

    def execute(self, **kwargs: Any) -> Any:
        task = kwargs.get("task")

        if not task:
            return "Error: You must provide a 'task' string to ask Jules."

        if not is_connected():
            return "Error: Chhaya is currently running entirely offline. Cannot reach Jules. You must complete the task yourself using local tools."

        api_key = settings.external_agents.jules_api_key
        url = settings.external_agents.jules_url

        if not api_key:
            return "Error: Jules API key is not configured. Cannot delegate. Ask the human administrator to set JULES_API_KEY in the environment."

        logger.info("Delegating task to Jules", task=task)

        try:
            with httpx.Client() as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {"task": task}

                # We use a long timeout as Jules might take a while to finish a complex task
                response = client.post(url, json=payload, headers=headers, timeout=300.0)

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", "Jules completed the task but returned no specific output.")
                    logger.info("Successfully received response from Jules")
                    return f"Jules responded: {result}"
                else:
                    logger.warning("Jules API returned an error", status_code=response.status_code, text=response.text)
                    return f"Error: Jules API returned status {response.status_code}. You might need to try a different approach."

        except httpx.RequestError as e:
            logger.error("Failed to connect to Jules API", error=str(e))
            return f"Error: Failed to connect to Jules API: {e}. You must attempt the task yourself."
