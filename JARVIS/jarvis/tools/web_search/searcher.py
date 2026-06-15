"""
jarvis/tools/web_search/searcher.py

Web search tool for JARVIS using DuckDuckGo (free, no API key).
Falls back to Google via browser automation if DuckDuckGo fails.
Also handles: YouTube search, GitHub search, Wikipedia lookup,
file downloads, and general web browsing.
"""

import re
import time
import urllib.parse
from typing import List, Dict, Optional

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

import requests
from bs4 import BeautifulSoup


class WebSearcher:
    """Multi-source web search with content extraction."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web. Returns list of {title, url, snippet} dicts.
        Tries DuckDuckGo first, then falls back to Bing scrape.
        """
        if DDGS_AVAILABLE:
            try:
                return self._ddg_search(query, max_results)
            except Exception as e:
                print(f"  [WebSearch] DuckDuckGo failed: {e} — trying fallback")

        return self._bing_scrape(query, max_results)

    def _ddg_search(self, query: str, max_results: int) -> List[Dict]:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "url":     r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results

    def _bing_scrape(self, query: str, max_results: int) -> List[Dict]:
        """Fallback: scrape Bing search results."""
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select(".b_algo")[:max_results]:
                title_el = item.select_one("h2 a")
                snip_el  = item.select_one(".b_caption p")
                if title_el:
                    results.append({
                        "title":   title_el.get_text(strip=True),
                        "url":     title_el.get("href", ""),
                        "snippet": snip_el.get_text(strip=True) if snip_el else "",
                    })
            return results
        except Exception as e:
            print(f"  [WebSearch] Bing scrape failed: {e}")
            return []

    def fetch_page_text(self, url: str, max_chars: int = 3000) -> str:
        """Fetch the main text content of a webpage."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Collapse blank lines
            lines = [l for l in text.splitlines() if l.strip()]
            clean = "\n".join(lines)
            return clean[:max_chars]
        except Exception as e:
            return f"Error fetching page: {e}"

    def search_youtube(self, query: str) -> str:
        """Return YouTube search URL for a query."""
        return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

    def search_github(self, query: str) -> List[Dict]:
        """Search GitHub repos using the public API (no auth needed for basic search)."""
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page=5"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            data = resp.json()
            results = []
            for item in data.get("items", []):
                results.append({
                    "name":        item.get("full_name", ""),
                    "url":         item.get("html_url", ""),
                    "description": item.get("description", ""),
                    "stars":       item.get("stargazers_count", 0),
                    "language":    item.get("language", ""),
                })
            return results
        except Exception as e:
            print(f"  [WebSearch] GitHub search failed: {e}")
            return []

    def wikipedia_summary(self, topic: str) -> str:
        """Get a Wikipedia summary for a topic."""
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            data = resp.json()
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            return f"{extract}\n\nSource: {page_url}"
        except Exception as e:
            return f"Wikipedia lookup failed: {e}"

    def download_file(self, url: str, save_path: str) -> str:
        """Download a file from a URL."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=60, stream=True)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return f"Downloaded to: {save_path}"
        except Exception as e:
            return f"Download failed: {e}"

    def format_results(self, results: List[Dict]) -> str:
        """Format search results for display."""
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   {r['url']}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:150]}...")
            lines.append("")
        return "\n".join(lines)


# Singleton
_searcher = None

def get_searcher() -> WebSearcher:
    global _searcher
    if _searcher is None:
        _searcher = WebSearcher()
    return _searcher


def web_search_tool(query: str, fetch_content: bool = False) -> str:
    """
    LangChain-compatible tool function.
    Returns formatted search results as a string.
    """
    searcher = get_searcher()

    # Detect special search types
    q_lower = query.lower()

    if "github" in q_lower or "repository" in q_lower or "repo" in q_lower:
        results = searcher.search_github(query)
        if results:
            lines = [f"GitHub search results for '{query}':\n"]
            for r in results:
                lines.append(f"  ⭐ {r['stars']}  {r['name']}")
                lines.append(f"     {r['description']}")
                lines.append(f"     {r['url']}")
                lines.append("")
            return "\n".join(lines)

    if "wikipedia" in q_lower or q_lower.startswith("what is ") or q_lower.startswith("who is "):
        topic = re.sub(r"^(what is |who is |wikipedia )", "", q_lower).strip()
        return searcher.wikipedia_summary(topic)

    if "youtube" in q_lower:
        yt_url = searcher.search_youtube(query.replace("youtube", "").strip())
        return f"YouTube search URL: {yt_url}"

    # Standard web search
    results = searcher.search(query, max_results=5)
    formatted = searcher.format_results(results)

    if fetch_content and results:
        # Fetch content from top result
        top_url = results[0]["url"]
        content = searcher.fetch_page_text(top_url)
        formatted += f"\n\n--- Content from top result ---\n{content}"

    return formatted
