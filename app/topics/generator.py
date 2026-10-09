"""Generate metadata-only candidates when the reservoir is low."""

from __future__ import annotations

from app.llm.router import LLMRouter
from app.topics.deduplication import normalize_topic_id
from app.topics.models import TopicCandidate
from app.topics.repository import TopicRepository


class TopicGenerator:
    def __init__(self, router: LLMRouter, repository: TopicRepository, *, pool_size: int, low_watermark: int) -> None:
        self._router, self._repository = router, repository
        self._pool_size, self._low_watermark = pool_size, low_watermark

    def refill_if_needed(self) -> list[TopicCandidate]:
        if self._repository.pool_size() > self._low_watermark:
            return []
        excluded = self._repository.pool_ids() | self._repository.sent_ids()
        requested = self._pool_size - self._repository.pool_size()
        prompt = (
            f"Generate {requested} intellectually serendipitous curiosity-topic candidates across many unrelated fields. "
            "These are metadata only, not articles. Avoid technology-only selections and avoid obvious variants of excluded IDs: "
            f"{', '.join(sorted(excluded)) or '(none)'}. "
            "Return {\"topics\":[{\"title\":string,\"summary\":string,\"category\":string}]}"
        )
        payload = self._router.generate_structured(prompt, task="topic_generation")
        accepted: list[TopicCandidate] = []
        seen = set(excluded)
        for item in payload.get("topics", []):
            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
            category = str(item.get("category", "")).strip()
            identifier = normalize_topic_id(title)
            if title and summary and category and identifier and identifier not in seen:
                accepted.append(TopicCandidate(title=title, summary=summary, category=category, normalized_id=identifier))
                seen.add(identifier)
        self._repository.add_to_pool(accepted)
        return accepted
