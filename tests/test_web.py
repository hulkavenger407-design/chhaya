"""
Tests for Chhaya FastAPI Web Interface.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from chhaya.interfaces.web import app, AppState
from chhaya.domain.models import AgentBlueprint

# We mock the entire AppState to prevent real DB/LLM initializations
@pytest.fixture(autouse=True)
def mock_app_state():
    with patch("chhaya.interfaces.web.AppState") as mock_state_class:
        mock_state = mock_state_class.return_value

        # Setup common mock returns
        mock_blueprint = AgentBlueprint(name="web_bot", role="Web tester", system_prompt="test")
        mock_state.factory.create_agent.return_value = mock_blueprint
        mock_state.agent_registry.load_blueprint.return_value = mock_blueprint
        mock_state.agent_registry.list_blueprints.return_value = [mock_blueprint]
        mock_state.execution.run.return_value = "Run successful from web!"

        app.state.chhaya = mock_state
        yield mock_state


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "system": "chhaya"}


def test_list_agents(client, mock_app_state):
    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "web_bot"
    mock_app_state.agent_registry.list_blueprints.assert_called_once()


def test_create_agent(client, mock_app_state):
    response = client.post(
        "/api/agents",
        json={"brief": "Make a web bot"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "web_bot"
    mock_app_state.factory.create_agent.assert_called_once_with(brief="Make a web bot")


def test_get_agent(client, mock_app_state):
    response = client.get("/api/agents/web_bot")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "web_bot"
    mock_app_state.agent_registry.load_blueprint.assert_called_once_with("web_bot")


def test_get_agent_not_found(client, mock_app_state):
    mock_app_state.agent_registry.load_blueprint.return_value = None

    response = client.get("/api/agents/ghost_bot")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_run_agent(client, mock_app_state):
    # Mock workspace to avoid file operations
    with patch("chhaya.interfaces.web.LocalWorkspace"):
        response = client.post(
            "/api/agents/web_bot/run",
            json={"task": "Do a web task"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"] == "Run successful from web!"

        mock_app_state.agent_registry.load_blueprint.assert_called_once_with("web_bot")
        mock_app_state.execution.run.assert_called_once()
