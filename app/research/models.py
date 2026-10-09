from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    snippet: str
    published_date: str | None = None


@dataclass(frozen=True)
class ResearchBrief:
    topic_title: str
    overview: str
    key_claims: list[str]
    uncertainty: str
    sources: list[Source]
