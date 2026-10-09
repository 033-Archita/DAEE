from __future__ import annotations

from dataclasses import dataclass

from app.news.models import NewsItem
from app.story.models import CuriosityStory


@dataclass(frozen=True)
class DailyMagazine:
    greeting: str
    stories: list[CuriosityStory]
    news: list[NewsItem]
    rabbit_hole_question: str
