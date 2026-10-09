from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.llm.router import LLMRouter
from app.news.models import NewsItem
from app.research.models import Source
from app.research.search import SearchProvider


class NewsResearcher:
    def __init__(self, search: SearchProvider, llm: LLMRouter, *, max_results: int) -> None:
        self._search, self._llm, self._max_results = search, llm, max_results

    def recent_developments(self, now: datetime | None = None) -> list[NewsItem]:
        now = now or datetime.now(UTC)
        since = now - timedelta(hours=24)
        sources = self._search.search(f"major India world science economy developments after {since.date().isoformat()}", max_results=self._max_results)
        evidence = "\n".join(f"- {source.title}: {source.snippet} ({source.url})" for source in sources)
        payload = self._llm.generate_structured(
            "Select only meaningful, source-supported developments from approximately the last 24 hours. Do not force categories and do not invent events. "
            "Return {\"items\":[{\"headline\":string,\"summary\":string,\"significance\":string,\"source_indexes\":[integer]}]}.\nEvidence:\n" + evidence,
            task="news_synthesis",
        )
        items: list[NewsItem] = []
        for item in payload.get("items", []):
            selected = [sources[index] for index in item.get("source_indexes", []) if isinstance(index, int) and 0 <= index < len(sources)]
            if item.get("headline") and item.get("summary") and selected:
                items.append(NewsItem(headline=str(item["headline"]), summary=str(item["summary"]), significance=str(item.get("significance", "")), sources=selected))
        return items
