"""Client for Google's current Web Search Service API."""

from __future__ import annotations

from urllib.parse import urlencode

import requests


SEARCH_ENDPOINT = "https://websearchservice.googleapis.com/v1:search"


class GoogleWebSearchClient:
    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session or requests.Session()

    def search(self, query: str, user_ip: str, page_size: int = 5) -> list[dict[str, object]]:
        if not self.settings.google_web_search_configured:
            raise RuntimeError("Google web search is not configured")
        if not query or not query.strip():
            raise ValueError("search query is required")
        if not user_ip:
            raise ValueError("user IP address is required for Google web search")

        params = {
            "searchQuery.query": query.strip(),
            "clientContext.clientId": self.settings.google_web_search_client_id,
            "userContext.ipAddress": user_ip,
            "pageSize": max(1, min(int(page_size), 10)),
        }
        try:
            response = self.session.get(
                SEARCH_ENDPOINT,
                params=params,
                headers={"X-Goog-Api-Key": self.settings.google_web_search_api_key},
                timeout=(5, 20),
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise RuntimeError("Google web search request failed") from exc
        except ValueError as exc:
            raise RuntimeError("Google web search returned invalid JSON") from exc

        return self._normalize_results(payload)

    @staticmethod
    def _normalize_results(payload: dict) -> list[dict[str, object]]:
        raw_results = payload.get("searchResults") or payload.get("results") or []
        normalized: list[dict[str, object]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name")
            url = item.get("url") or item.get("link")
            snippet = item.get("snippet") or item.get("description") or item.get("text")
            if isinstance(item.get("result"), dict):
                result = item["result"]
                title = title or result.get("title") or result.get("name")
                url = url or result.get("url") or result.get("link")
                snippet = snippet or result.get("snippet") or result.get("description")
            if not title and not url and not snippet:
                continue
            normalized.append(
                {
                    "title": str(title or "Untitled result"),
                    "url": str(url or ""),
                    "snippet": str(snippet or ""),
                }
            )
        return normalized
