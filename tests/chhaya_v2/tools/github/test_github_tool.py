import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from chhaya_v2.tools.github.github_tool import GitHubTool

@pytest.mark.asyncio
async def test_fetch_updates():
    tool = GitHubTool()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await tool.fetch_updates()
        assert "successfully" in result
        mock_exec.assert_called_once_with(
            "git", "fetch", "origin", "main",
            cwd=".",
            stdout=-1,
            stderr=-1
        )

@pytest.mark.asyncio
async def test_get_pending_commits():
    tool = GitHubTool()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"1234567 feat: new feature\nabcdefg fix: bug", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        commits = await tool.get_pending_commits()
        assert len(commits) == 2
        assert commits[0] == "1234567 feat: new feature"

@pytest.mark.asyncio
async def test_apply_updates():
    tool = GitHubTool()

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await tool.apply_updates()
        assert "Successfully applied updates" in result
        # Should be called twice: once for stash, once for pull
        assert mock_exec.call_count == 2
