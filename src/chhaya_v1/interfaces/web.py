"""
FastAPI Web Interface for Chhaya.
Provides a REST API for the Agent Factory.
"""

from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import structlog

from chhaya_v1.core.config import settings
from chhaya_v1.core.event_bus import InMemoryEventBus
from chhaya_v1.infrastructure.storage.sqlite import SQLiteStorageProvider
from chhaya_v1.infrastructure.memory.chroma import ChromaMemoryProvider
from chhaya_v1.infrastructure.llm.ollama import OllamaProvider
from chhaya_v1.infrastructure.workspace.local import LocalWorkspace
from chhaya_v1.core.tool_registry import ToolRegistry
from chhaya_v1.tools.memory_tool import SaveMemoryTool
from chhaya_v1.core.agent_registry import AgentRegistry
from chhaya_v1.core.factory import AgentFactory
from chhaya_v1.core.execution_engine import ExecutionEngine
from chhaya_v1.core.reflection_engine import ReflectionEngine
from chhaya_v1.domain.models import AgentBlueprint

logger = structlog.get_logger(__name__)


# Application State Container
class AppState:
    def __init__(self):
        self.event_bus = InMemoryEventBus()
        self.storage = SQLiteStorageProvider(database_url=settings.storage.database_url)
        self.memory = ChromaMemoryProvider(persist_directory=settings.memory.path)
        self.llm = OllamaProvider(base_url=settings.ollama_base_url)

        self.tool_registry = ToolRegistry()
        # Register built-in tools
        self.tool_registry.register(SaveMemoryTool(memory_provider=self.memory))

        self.agent_registry = AgentRegistry(storage_provider=self.storage)

        self.factory = AgentFactory(
            llm_provider=self.llm,
            agent_registry=self.agent_registry,
            tool_registry=self.tool_registry,
            event_bus=self.event_bus
        )
        self.execution = ExecutionEngine(
            llm_provider=self.llm,
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            memory_provider=self.memory
        )
        self.reflection = ReflectionEngine(
            llm_provider=self.llm,
            agent_registry=self.agent_registry,
            tool_registry=self.tool_registry,
            event_bus=self.event_bus
        )


app = FastAPI(
    title="Chhaya Agent Factory API",
    description="REST interface for managing and running autonomous agents.",
    version="0.1.0"
)

# Attach state to app
state = AppState()
app.state.chhaya = state


# --- Request/Response Models ---

class CreateAgentRequest(BaseModel):
    brief: str

class RunAgentRequest(BaseModel):
    task: str

class RunResponse(BaseModel):
    status: str
    result: str


# --- Routes ---

@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok", "system": "chhaya"}


@app.get("/api/agents", response_model=List[AgentBlueprint])
def list_agents() -> List[AgentBlueprint]:
    """Retrieves all registered agents (latest versions)."""
    return app.state.chhaya.agent_registry.list_blueprints()


@app.post("/api/agents", response_model=AgentBlueprint)
def create_agent(req: CreateAgentRequest) -> AgentBlueprint:
    """Uses the reasoning model to design and register a new agent."""
    try:
        blueprint = app.state.chhaya.factory.create_agent(brief=req.brief)
        return blueprint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Web API create agent failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error during agent creation.")


@app.get("/api/agents/{agent_name}", response_model=AgentBlueprint)
def get_agent(agent_name: str) -> AgentBlueprint:
    """Retrieves an agent blueprint by name."""
    blueprint = app.state.chhaya.agent_registry.load_blueprint(agent_name)
    if not blueprint:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")
    return blueprint


@app.post("/api/agents/{agent_name}/run", response_model=RunResponse)
def run_agent(agent_name: str, req: RunAgentRequest) -> RunResponse:
    """Executes an agent on a specific task."""
    blueprint = app.state.chhaya.agent_registry.load_blueprint(agent_name)
    if not blueprint:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    workspace = LocalWorkspace(agent_name=agent_name, base_path=settings.workspace.base_path)

    try:
        result = app.state.chhaya.execution.run(blueprint=blueprint, task=req.task, workspace=workspace)
        return RunResponse(status="success", result=result)
    except RuntimeError as e:
        logger.error("Web API run agent failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")
