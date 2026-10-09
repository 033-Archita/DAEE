"""Search abstraction; Tavily is the initial concrete web-search provider."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.research.models import Source


class SearchError(RuntimeError):
    pass


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, *, max_results: int) -> list[Source]: ...


class TavilySearchProvider(SearchProvider):
    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def search(self, query: str, *, max_results: int) -> list[Source]:
        if not self._api_key:
            raise SearchError("TAVILY_API_KEY is required for web research.")
        body = json.dumps({"api_key": self._api_key, "query": query, "max_results": max_results, "search_depth": "advanced", "include_answer": False}).encode()
        request = Request(self.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise SearchError("Web search request failed.") from error
        return [Source(title=item.get("title", "Untitled source"), url=item["url"], snippet=item.get("content", ""), published_date=item.get("published_date")) for item in payload.get("results", []) if item.get("url")]
