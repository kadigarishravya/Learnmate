"""Compatibility module for the web-search client."""

from __future__ import annotations

import requests


SEARCH_ENDPOINT = "https://api.tavily.com/search"


class TavilyWebSearchClient:
    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session or requests.Session()

    def search(self, query: str, page_size: int = 5) -> list[dict[str, object]]:
        if not self.settings.tavily_configured:
            raise RuntimeError("Tavily web search is not configured")
        if not query or not query.strip():
            raise ValueError("search query is required")

        payload = {
            "query": query.strip(),
            "topic": "general",
            "search_depth": "basic",
            "max_results": max(1, min(int(page_size), 10)),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        try:
            response = self.session.post(
                SEARCH_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.settings.tavily_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=(5, 20),
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise RuntimeError("Tavily web search request failed") from exc
        except ValueError as exc:
            raise RuntimeError("Tavily web search returned invalid JSON") from exc

        results: list[dict[str, object]] = []
        for item in data.get("results", []):
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": str(item.get("title") or "Untitled result"),
                    "url": str(item.get("url") or ""),
                    "snippet": str(item.get("content") or ""),
                }
            )
        return results


# Keep the old import name temporarily so the existing route remains compatible.
GoogleWebSearchClient = TavilyWebSearchClient
