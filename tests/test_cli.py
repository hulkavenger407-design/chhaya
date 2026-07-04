"""
Tests for Chhaya CLI Interface.
"""

from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from chhaya.interfaces.cli import app
from chhaya.domain.models import AgentBlueprint

runner = CliRunner()


@pytest.fixture
def mock_ctx():
    # Because `ctx` is instantiated globally via the Typer callback, we patch SystemContainer directly
    with patch("chhaya.interfaces.cli.SystemContainer") as mock_container:
        mock_instance = mock_container.return_value

        # Setup common mock returns
        mock_blueprint = AgentBlueprint(name="test_bot", role="tester", system_prompt="test")
        mock_instance.factory.create_agent.return_value = mock_blueprint
        mock_instance.agent_registry.load_blueprint.return_value = mock_blueprint
        mock_instance.execution.run.return_value = "Success"
        mock_instance.reflection.reflect_and_improve.return_value = mock_blueprint

        yield mock_instance


def test_cli_create_agent(mock_ctx):
    # Set the specific mock return for this test
    mock_blueprint = AgentBlueprint(name="cli_bot", role="CLI tester", system_prompt="Test.", version=1, model_tier="7b")
    mock_ctx.factory.create_agent.return_value = mock_blueprint

    result = runner.invoke(app, ["create", "Make a CLI tester bot"])

    assert result.exit_code == 0
    assert "Successfully created agent: cli_bot" in result.stdout
    mock_ctx.factory.create_agent.assert_called_once_with(brief="Make a CLI tester bot")


def test_cli_run_agent(mock_ctx):
    mock_blueprint = AgentBlueprint(name="runner_bot", role="Runner", system_prompt="Run.")
    mock_ctx.agent_registry.load_blueprint.return_value = mock_blueprint
    mock_ctx.execution.run.return_value = "Run successful!"

    with patch("chhaya.interfaces.cli.LocalWorkspace") as mock_workspace:
        result = runner.invoke(app, ["run", "runner_bot", "Do a task"])

        assert result.exit_code == 0
        assert "Running agent 'runner_bot' on task: 'Do a task'" in result.stdout
        assert "Run successful!" in result.stdout

        mock_ctx.agent_registry.load_blueprint.assert_called_once_with("runner_bot")
        mock_ctx.execution.run.assert_called_once()


def test_cli_run_agent_not_found(mock_ctx):
    mock_ctx.agent_registry.load_blueprint.return_value = None

    result = runner.invoke(app, ["run", "ghost_bot", "task"])

    assert result.exit_code == 1
    assert "Error: Agent 'ghost_bot' not found" in result.stdout


def test_cli_reflect_agent(mock_ctx):
    mock_blueprint = AgentBlueprint(name="smart_bot", role="Genius", system_prompt="Be smart.", version=2)
    mock_ctx.reflection.reflect_and_improve.return_value = mock_blueprint

    result = runner.invoke(app, [
        "reflect", "smart_bot",
        "--task", "solve math",
        "--result", "4",
        "--feedback", "wrong"
    ])

    assert result.exit_code == 0
    assert "Successfully proposed new version!" in result.stdout
    assert "smart_bot" in result.stdout

    mock_ctx.reflection.reflect_and_improve.assert_called_once_with(
        blueprint_name="smart_bot",
        task="solve math",
        result="4",
        feedback="wrong"
    )
