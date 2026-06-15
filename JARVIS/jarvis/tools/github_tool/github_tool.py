"""
jarvis/tools/github_tool/github_tool.py

GitHub integration for JARVIS (no API key needed for public repos).
Capabilities:
- Search repositories
- Read README and source files from any public repo
- Clone repos locally
- Fetch code snippets, issues, trending repos
- Learn from open-source code on command
"""

import os
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Optional


GITHUB_API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "JARVIS-AI-Assistant/2.0",
}

# Add token if available (optional — raises rate limit from 60 to 5000/hr)
_token = os.getenv("GITHUB_TOKEN")
if _token:
    HEADERS["Authorization"] = f"token {_token}"


class GitHubTool:

    def search_repos(self, query: str, language: str = None, max_results: int = 5) -> List[Dict]:
        """Search GitHub repositories."""
        q = query
        if language:
            q += f" language:{language}"
        url = f"{GITHUB_API}/search/repositories?q={requests.utils.quote(q)}&sort=stars&per_page={max_results}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [
                {
                    "name":        item["full_name"],
                    "url":         item["html_url"],
                    "description": item.get("description", ""),
                    "stars":       item["stargazers_count"],
                    "language":    item.get("language", ""),
                    "clone_url":   item["clone_url"],
                    "default_branch": item.get("default_branch", "main"),
                }
                for item in items
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def get_readme(self, owner: str, repo: str) -> str:
        """Fetch README from a GitHub repo."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            import base64
            content = resp.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="replace")[:5000]
        except Exception as e:
            return f"Could not fetch README: {e}"

    def get_file(self, owner: str, repo: str, file_path: str, branch: str = "main") -> str:
        """Read a specific file from a GitHub repo."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            import base64
            content = resp.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="replace")[:8000]
        except Exception as e:
            return f"Could not fetch file: {e}"

    def list_repo_files(self, owner: str, repo: str, path: str = "", branch: str = "main") -> List[str]:
        """List files/directories in a repo."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, list):
                return [
                    f"{'📁' if i['type']=='dir' else '📄'} {i['name']} ({i['type']})"
                    for i in items
                ]
            return []
        except Exception as e:
            return [f"Error: {e}"]

    def get_trending(self, language: str = "", period: str = "daily") -> str:
        """
        Get trending repos from GitHub trending page.
        Uses web scrape since there's no official API.
        """
        from bs4 import BeautifulSoup
        url = f"https://github.com/trending/{language}?since={period}"
        try:
            resp = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.Box-row")[:10]
            lines = [f"Trending GitHub repos ({language or 'all languages'}, {period}):\n"]
            for art in articles:
                name_el = art.select_one("h2 a")
                desc_el = art.select_one("p")
                stars_el = art.select_one("a.Link--muted:nth-of-type(1)")
                if name_el:
                    name = name_el.get_text(strip=True).replace("\n", "").replace(" ", "")
                    desc = desc_el.get_text(strip=True) if desc_el else ""
                    stars = stars_el.get_text(strip=True) if stars_el else ""
                    lines.append(f"  ⭐ {stars}  {name}")
                    if desc:
                        lines.append(f"     {desc[:100]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Could not fetch trending: {e}"

    def clone_repo(self, clone_url: str, target_dir: str = None) -> str:
        """Clone a GitHub repo to local machine."""
        if target_dir is None:
            username = os.getenv("USERNAME", "User")
            target_dir = str(Path(f"C:/Users/{username}/Documents/JARVIS_Repos"))
        os.makedirs(target_dir, exist_ok=True)
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url],
                capture_output=True, text=True, timeout=120,
                cwd=target_dir
            )
            if result.returncode == 0:
                return f"Cloned successfully to {target_dir}"
            return f"Clone failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Clone timed out (>2 min)"
        except Exception as e:
            return f"Clone error: {e}"

    def learn_from_repo(self, owner: str, repo: str) -> str:
        """
        Read key files from a repo and return a learning summary.
        JARVIS uses this to understand open-source projects on command.
        """
        readme = self.get_readme(owner, repo)
        files = self.list_repo_files(owner, repo)
        summary = f"=== {owner}/{repo} ===\n\nREADME (first 2000 chars):\n{readme[:2000]}\n\nFile structure:\n"
        summary += "\n".join(files[:20])
        return summary


# Singleton
_github = None

def get_github() -> GitHubTool:
    global _github
    if _github is None:
        _github = GitHubTool()
    return _github


def github_tool(action: str, **kwargs) -> str:
    """
    LangChain-compatible entry point.
    action: search | readme | file | trending | clone | learn
    """
    gh = get_github()
    if action == "search":
        results = gh.search_repos(kwargs.get("query", ""), kwargs.get("language"))
        lines = []
        for r in results:
            if "error" in r:
                return r["error"]
            lines.append(f"⭐ {r['stars']:,}  {r['name']}")
            lines.append(f"   {r['description']}")
            lines.append(f"   {r['url']}\n")
        return "\n".join(lines) or "No results."
    elif action == "readme":
        return gh.get_readme(kwargs["owner"], kwargs["repo"])
    elif action == "file":
        return gh.get_file(kwargs["owner"], kwargs["repo"], kwargs["path"])
    elif action == "trending":
        return gh.get_trending(kwargs.get("language", ""), kwargs.get("period", "daily"))
    elif action == "clone":
        return gh.clone_repo(kwargs["url"], kwargs.get("target_dir"))
    elif action == "learn":
        return gh.learn_from_repo(kwargs["owner"], kwargs["repo"])
    else:
        return f"Unknown action: {action}. Use: search, readme, file, trending, clone, learn"
