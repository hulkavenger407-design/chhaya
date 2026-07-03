import sys
import os
import asyncio
import structlog
from chhaya_v2.tools.github.github_tool import GitHubTool

logger = structlog.get_logger(__name__)

class AppUpdater:
    """System-level controller to orchestrate GitHub synchronization."""
    def __init__(self):
        self.github = GitHubTool()

    async def check_for_updates(self) -> str:
        """Checks if Jules has pushed any pending features to GitHub."""
        await self.github.fetch_updates()
        commits = await self.github.get_pending_commits()

        if not commits:
            return "No new features found from Jules. We are fully synced."

        pending_str = "\n".join([f"- {c}" for c in commits])
        return f"Found {len(commits)} pending features/updates from Jules:\n{pending_str}\n\nShall I apply these updates now?"

    async def apply_updates_and_restart(self) -> str:
        """Applies the updates from GitHub."""
        result = await self.github.apply_updates()

        # In a real deployed environment, an external watcher process would restart the main script
        # if we exit here. For Phase 4, we simply return the instruction to restart.
        if "Successfully" in result:
            logger.info("updates_applied_awaiting_restart")
            # os.execv(sys.executable, ['python'] + sys.argv) # Optional auto-restart logic

        return result
