"""
Command Line Interface for Chhaya.
Provides the primary user interaction surface using Typer.
"""

import sys
import asyncio
from typing import Any, Dict
import typer
from rich.console import Console
from rich.panel import Panel

from chhaya.core.config import settings
from chhaya.core.event_bus import InMemoryEventBus
from chhaya.infrastructure.storage.sqlite import SQLiteStorageProvider
from chhaya.infrastructure.memory.chroma import ChromaMemoryProvider
from chhaya.infrastructure.llm.ollama import OllamaProvider
from chhaya.infrastructure.workspace.local import LocalWorkspace
from chhaya.core.tool_registry import ToolRegistry
from chhaya.tools.memory_tool import SaveMemoryTool
from chhaya.core.agent_registry import AgentRegistry
from chhaya.core.factory import AgentFactory
from chhaya.core.execution_engine import ExecutionEngine
from chhaya.core.reflection_engine import ReflectionEngine
from chhaya.interfaces.voice import VoiceInterface

app = typer.Typer(help="Chhaya: Autonomous Agent Factory", no_args_is_help=True)
console = Console()


def cli_approval_callback(agent_name: str, tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Callback for CLI to request human-in-the-loop approval."""
    console.print(f"\n[bold yellow]🛡️  Guardrail Intercept: Approval Required[/bold yellow]")
    console.print(f"Agent [cyan]'{agent_name}'[/cyan] wants to run tool [cyan]'{tool_name}'[/cyan]")
    console.print(f"Arguments: {arguments}")

    return typer.confirm("Do you approve this action?", default=False)


class SystemContainer:
    """Dependency Injection container for the CLI context."""
    def __init__(self):
        self.event_bus = InMemoryEventBus()
        self.storage = SQLiteStorageProvider(database_url=settings.storage.database_url)
        self.memory = ChromaMemoryProvider(persist_directory=settings.memory.path)
        self.llm = OllamaProvider(base_url=settings.ollama_base_url)

        self.tool_registry = ToolRegistry()
        # Register built-in tools
        self.tool_registry.register(SaveMemoryTool(memory_provider=self.memory))

        self.agent_registry = AgentRegistry(storage_provider=self.storage)

        # Engines
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
            memory_provider=self.memory,
            approval_callback=cli_approval_callback
        )
        self.reflection = ReflectionEngine(
            llm_provider=self.llm,
            agent_registry=self.agent_registry,
            tool_registry=self.tool_registry,
            event_bus=self.event_bus
        )

# Global context to hold instantiated dependencies during CLI run
ctx: SystemContainer


@app.callback()
def main_callback():
    """
    Global setup for the Chhaya CLI.
    """
    global ctx
    try:
        ctx = SystemContainer()
    except Exception as e:
        console.print(f"[bold red]Failed to initialize system dependencies: {e}[/bold red]")
        sys.exit(1)


@app.command()
def create(brief: str = typer.Argument(..., help="Natural language brief describing the agent you want to create.")):
    """
    Use the Reasoning LLM to design and register a new Agent Blueprint.
    """
    console.print(f"🏭 [cyan]Designing agent based on brief:[/cyan] '{brief}'...")

    try:
        blueprint = ctx.factory.create_agent(brief=brief)
        console.print(Panel(
            f"[bold green]Successfully created agent:[/bold green] {blueprint.name}\n"
            f"[bold]Role:[/bold] {blueprint.role}\n"
            f"[bold]Tier:[/bold] {blueprint.model_tier.value}\n"
            f"[bold]Version:[/bold] {blueprint.version}",
            title="Agent Factory"
        ))
    except Exception as e:
        console.print(f"[bold red]Factory failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def run(
    agent_name: str = typer.Argument(..., help="The name of the agent to run."),
    task: str = typer.Argument(..., help="The specific task for the agent to execute.")
):
    """
    Execute a specific task using a registered agent.
    """
    blueprint = ctx.agent_registry.load_blueprint(agent_name)
    if not blueprint:
        console.print(f"[bold red]Error:[/bold red] Agent '{agent_name}' not found.")
        raise typer.Exit(code=1)

    console.print(f"🚀 [cyan]Running agent[/cyan] '{agent_name}' [cyan]on task:[/cyan] '{task}'...")

    # Create isolated workspace for this run
    workspace = LocalWorkspace(agent_name=agent_name, base_path=settings.workspace.base_path)

    try:
        result = ctx.execution.run(blueprint=blueprint, task=task, workspace=workspace)
        console.print(Panel(result, title=f"Result ({agent_name})"))
    except Exception as e:
        console.print(f"[bold red]Execution failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def reflect(
    agent_name: str = typer.Argument(..., help="The name of the agent to reflect upon."),
    task: str = typer.Option(..., help="The task the agent attempted."),
    result: str = typer.Option(..., help="The result the agent produced."),
    feedback: str = typer.Option(..., help="The feedback or error logs to learn from.")
):
    """
    Propose a new blueprint version based on feedback from a past run.
    """
    console.print(f"🧠 [cyan]Reflecting on agent[/cyan] '{agent_name}'...")

    try:
        new_blueprint = ctx.reflection.reflect_and_improve(
            blueprint_name=agent_name,
            task=task,
            result=result,
            feedback=feedback
        )
        console.print(Panel(
            f"[bold green]Successfully proposed new version![/bold green]\n"
            f"[bold]Agent:[/bold] {new_blueprint.name}\n"
            f"[bold]New Version:[/bold] {new_blueprint.version}\n"
            f"[bold]Updated Prompt:[/bold] {new_blueprint.system_prompt[:100]}...",
            title="Reflection Engine"
        ))
    except ValueError as e:
        console.print(f"[bold red]Reflection Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def voice():
    """
    Starts the continuous voice assistant loop with wake-word detection.
    """
    workspace = LocalWorkspace(agent_name="voice_assistant", base_path=settings.workspace.base_path)
    voice_ui = VoiceInterface(execution_engine=ctx.execution, workspace=workspace)

    # Run the async loop
    asyncio.run(voice_ui.start_loop())


if __name__ == "__main__":
    app()
