"""
Tests for AskJulesTool.
"""

from unittest.mock import patch, MagicMock
import pytest
import httpx

from chhaya_v1.tools.jules_tool import AskJulesTool


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.Client.post") as mock_post:
        yield mock_post


@pytest.fixture
def mock_is_connected():
    with patch("chhaya_v1.tools.jules_tool.is_connected") as mock_conn:
        yield mock_conn


@pytest.fixture
def mock_settings():
    with patch("chhaya_v1.tools.jules_tool.settings") as settings:
        yield settings


def test_jules_tool_success(mock_httpx_post, mock_is_connected, mock_settings):
    mock_is_connected.return_value = True
    mock_settings.external_agents.jules_api_key = "test_key"
    mock_settings.external_agents.jules_url = "https://test.jules.ai/v1/tasks"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "I am Jules. I solved it."}
    mock_httpx_post.return_value = mock_response

    tool = AskJulesTool()
    result = tool.execute(task="Solve P vs NP")

    assert "Jules responded: I am Jules. I solved it." in result
    mock_httpx_post.assert_called_once()

    call_kwargs = mock_httpx_post.call_args.kwargs
    assert call_kwargs["json"]["task"] == "Solve P vs NP"
    assert call_kwargs["headers"]["Authorization"] == "Bearer test_key"


def test_jules_tool_offline(mock_is_connected):
    mock_is_connected.return_value = False

    tool = AskJulesTool()
    result = tool.execute(task="Help me")

    assert "Error: Chhaya is currently running entirely offline" in result


def test_jules_tool_missing_api_key(mock_is_connected, mock_settings):
    mock_is_connected.return_value = True
    mock_settings.external_agents.jules_api_key = None

    tool = AskJulesTool()
    result = tool.execute(task="Help me")

    assert "Error: Jules API key is not configured" in result


def test_jules_tool_api_error(mock_httpx_post, mock_is_connected, mock_settings):
    mock_is_connected.return_value = True
    mock_settings.external_agents.jules_api_key = "test_key"

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_httpx_post.return_value = mock_response

    tool = AskJulesTool()
    result = tool.execute(task="Break the API")

    assert "Error: Jules API returned status 500" in result


def test_jules_tool_connection_error(mock_httpx_post, mock_is_connected, mock_settings):
    mock_is_connected.return_value = True
    mock_settings.external_agents.jules_api_key = "test_key"

    mock_httpx_post.side_effect = httpx.RequestError("Connection timeout")

    tool = AskJulesTool()
    result = tool.execute(task="Timeout test")

    assert "Error: Failed to connect to Jules API" in result
