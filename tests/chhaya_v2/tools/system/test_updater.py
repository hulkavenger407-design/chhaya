import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from chhaya_v2.tools.system.updater import AppUpdater

@pytest.mark.asyncio
async def test_check_for_updates_no_commits():
    updater = AppUpdater()
    with patch("chhaya_v2.tools.github.github_tool.GitHubTool.fetch_updates", new_callable=AsyncMock) as mock_fetch:
        with patch("chhaya_v2.tools.github.github_tool.GitHubTool.get_pending_commits", new_callable=AsyncMock) as mock_commits:
            mock_commits.return_value = []

            msg = await updater.check_for_updates()
            assert "fully synced" in msg
            mock_fetch.assert_called_once()

@pytest.mark.asyncio
async def test_check_for_updates_has_commits():
    updater = AppUpdater()
    with patch("chhaya_v2.tools.github.github_tool.GitHubTool.fetch_updates", new_callable=AsyncMock) as mock_fetch:
        with patch("chhaya_v2.tools.github.github_tool.GitHubTool.get_pending_commits", new_callable=AsyncMock) as mock_commits:
            mock_commits.return_value = ["123 feat: x"]

            msg = await updater.check_for_updates()
            assert "Found 1 pending features" in msg
            assert "123 feat: x" in msg

@pytest.mark.asyncio
async def test_apply_updates_and_restart():
    updater = AppUpdater()
    with patch("chhaya_v2.tools.github.github_tool.GitHubTool.apply_updates", new_callable=AsyncMock) as mock_apply:
        mock_apply.return_value = "Successfully applied"

        msg = await updater.apply_updates_and_restart()
        assert msg == "Successfully applied"
