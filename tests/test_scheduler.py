"""
Tests for Chhaya Agent Scheduler.
"""

from unittest.mock import MagicMock, patch
import pytest
import time

from chhaya_v1.core.scheduler import AgentScheduler
from chhaya_v1.core.event_bus import InMemoryEventBus
from chhaya_v1.domain.models import AgentBlueprint


class MockExecutionEngine:
    def __init__(self):
        self.runs = []

    def run(self, blueprint, task, workspace):
        self.runs.append((blueprint.name, task))


class MockAgentRegistry:
    def __init__(self, blueprint=None):
        self.blueprint = blueprint

    def load_blueprint(self, name):
        return self.blueprint if self.blueprint and self.blueprint.name == name else None


@pytest.fixture
def scheduler_deps():
    execution = MockExecutionEngine()

    blueprint = AgentBlueprint(name="worker", role="Worker", system_prompt="Work.")
    registry = MockAgentRegistry(blueprint=blueprint)

    event_bus = InMemoryEventBus()

    return execution, registry, event_bus


def test_scheduler_cron(scheduler_deps):
    execution, registry, event_bus = scheduler_deps

    scheduler = AgentScheduler(execution, registry, event_bus)

    try:
        # Schedule for a time that is practically always "now" or "next minute"
        # In a real test we just verify the job was added to apscheduler correctly
        job_id = scheduler.schedule_cron("worker", "do cron work", "* * * * *")

        assert job_id is not None

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].name.startswith("cron_worker_")
    finally:
        scheduler.shutdown()


def test_scheduler_event_trigger(scheduler_deps):
    execution, registry, event_bus = scheduler_deps

    scheduler = AgentScheduler(execution, registry, event_bus)

    try:
        # Schedule on event
        scheduler.schedule_on_event("worker", "process file {filename}", "file_uploaded")

        # Fire event
        with patch("chhaya_v1.core.scheduler.LocalWorkspace"):
            event_bus.publish("file_uploaded", {"filename": "data.csv"})

            # APScheduler runs in a background thread, so we need to wait a tiny bit
            # for it to execute
            time.sleep(0.1)

            assert len(execution.runs) == 1
            assert execution.runs[0] == ("worker", "process file data.csv")
    finally:
        scheduler.shutdown()


def test_scheduler_event_trigger_missing_key(scheduler_deps):
    execution, registry, event_bus = scheduler_deps

    scheduler = AgentScheduler(execution, registry, event_bus)

    try:
        scheduler.schedule_on_event("worker", "process file {filename}", "file_uploaded")

        with patch("chhaya_v1.core.scheduler.LocalWorkspace"):
            # Fire event WITHOUT the expected 'filename' key
            event_bus.publish("file_uploaded", {"other_key": "data.csv"})

            time.sleep(0.1)

            # Should still run but fall back to the unformatted template string
            assert len(execution.runs) == 1
            assert execution.runs[0] == ("worker", "process file {filename}")
    finally:
        scheduler.shutdown()
