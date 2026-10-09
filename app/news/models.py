from __future__ import annotations

from dataclasses import dataclass

from app.research.models import Source


@dataclass(frozen=True)
class NewsItem:
    headline: str
    summary: str
    significance: str
    sources: list[Source]
