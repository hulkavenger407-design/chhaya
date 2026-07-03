"""
Scheduler for Chhaya.
Provides cron-like scheduling and event-triggered background tasks for autonomous agents.
"""

from typing import Any, Callable, Dict, Optional
import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from chhaya_v1.interfaces.event_bus import EventBus
from chhaya_v1.core.execution_engine import ExecutionEngine
from chhaya_v1.core.agent_registry import AgentRegistry
from chhaya_v1.infrastructure.workspace.local import LocalWorkspace
from chhaya_v1.core.config import settings

logger = structlog.get_logger(__name__)


class AgentScheduler:
    """
    Manages autonomous agent runs based on time (cron) or system events.
    """

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        agent_registry: AgentRegistry,
        event_bus: EventBus
    ):
        self.execution = execution_engine
        self.registry = agent_registry
        self.event_bus = event_bus

        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Agent Scheduler started.")

    def _execute_agent(self, agent_name: str, task: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Internal wrapper to load the blueprint, setup the workspace, and run the agent.
        """
        logger.info("Scheduler triggering agent", agent=agent_name, task=task)

        blueprint = self.registry.load_blueprint(agent_name)
        if not blueprint:
            logger.error("Scheduler failed: Agent not found", agent=agent_name)
            return

        workspace = LocalWorkspace(agent_name=agent_name, base_path=settings.workspace.base_path)

        try:
            self.execution.run(blueprint=blueprint, task=task, workspace=workspace)
        except Exception as e:
            logger.error("Scheduler execution failed", agent=agent_name, error=str(e))

    def schedule_cron(self, agent_name: str, task: str, cron_expression: str) -> str:
        """
        Schedules an agent to run on a cron schedule.

        Args:
            agent_name: The name of the agent to run.
            task: The task to give the agent.
            cron_expression: A standard cron string (e.g., "0 9 * * 1" for Monday 9 AM).

        Returns:
            The APScheduler job ID.
        """
        trigger = CronTrigger.from_crontab(cron_expression)

        job = self.scheduler.add_job(
            func=self._execute_agent,
            trigger=trigger,
            args=[agent_name, task],
            name=f"cron_{agent_name}_{task[:10]}"
        )
        logger.info("Scheduled cron job", agent=agent_name, cron=cron_expression, job_id=job.id)
        return job.id

    def schedule_on_event(self, agent_name: str, task_template: str, event_type: str) -> None:
        """
        Schedules an agent to run whenever a specific event occurs on the Event Bus.

        Args:
            agent_name: The name of the agent to run.
            task_template: A string template that can use {payload_key} for formatting task strings.
            event_type: The name of the event to listen for.
        """

        def event_handler(payload: Dict[str, Any]):
            try:
                # Format the task template with the event payload
                task = task_template.format(**payload)
            except KeyError as e:
                logger.warning("Event payload missing key for task template", missing_key=str(e), payload=payload)
                task = task_template  # Fallback to unformatted if keys are missing

            # Submit to the apscheduler thread pool to avoid blocking the event bus
            self.scheduler.add_job(
                func=self._execute_agent,
                args=[agent_name, task, payload],
                name=f"event_{agent_name}_{event_type}"
            )

        self.event_bus.subscribe(event_type, event_handler)
        logger.info("Scheduled event trigger", agent=agent_name, event_type=event_type)

    def shutdown(self):
        """Shuts down the background scheduler."""
        self.scheduler.shutdown()
        logger.info("Agent Scheduler shutdown.")
