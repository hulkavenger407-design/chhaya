import asyncio
import subprocess
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class GitHubTool:
    """Tool for Chhaya to interact with GitHub to sync code updates."""
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = workspace_path

    async def fetch_updates(self, remote: str = "origin", branch: str = "main") -> str:
        """Fetches the latest commits from the remote repository."""
        logger.info("fetching_github_updates", remote=remote, branch=branch)
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "fetch", remote, branch,
                cwd=self.workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error("git_fetch_failed", error=error_msg)
                return f"Failed to fetch updates: {error_msg}"

            return "Updates fetched successfully. Ready to sync."
        except Exception as e:
            logger.error("git_fetch_exception", error=str(e))
            return f"Error during fetch: {str(e)}"

    async def get_pending_commits(self, remote: str = "origin", branch: str = "main") -> list[str]:
        """Gets a list of commits that are pending to be applied locally."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "log", f"HEAD..{remote}/{branch}", "--oneline",
                cwd=self.workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return []

            output = stdout.decode().strip()
            if not output:
                return []

            return output.split("\n")
        except Exception:
            return []

    async def apply_updates(self, remote: str = "origin", branch: str = "main") -> str:
        """Pulls and applies the latest changes from GitHub."""
        logger.info("applying_github_updates")
        try:
            # First stash any local uncommitted changes to prevent conflicts
            stash_process = await asyncio.create_subprocess_exec(
                "git", "stash",
                cwd=self.workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await stash_process.wait()

            # Then pull the new changes
            process = await asyncio.create_subprocess_exec(
                "git", "pull", remote, branch, "--rebase",
                cwd=self.workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error("git_pull_failed", error=error_msg)
                return f"Failed to apply updates: {error_msg}"

            return "Successfully applied updates from Jules! Please restart the system to load the new features."
        except Exception as e:
            logger.error("git_pull_exception", error=str(e))
            return f"Error during update: {str(e)}"
