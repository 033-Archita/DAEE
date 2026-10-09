"""Search first, then synthesize evidence into a structured research brief."""

from __future__ import annotations

from app.llm.router import LLMRouter
from app.research.models import ResearchBrief, Source
from app.research.search import SearchProvider
from app.topics.models import TopicCandidate


class TopicResearcher:
    def __init__(self, search: SearchProvider, llm: LLMRouter, *, max_results: int) -> None:
        self._search, self._llm, self._max_results = search, llm, max_results

    def research(self, topic: TopicCandidate) -> ResearchBrief:
        sources = self._search.search(f"{topic.title} reliable primary sources history explanation", max_results=self._max_results)
        if not sources:
            raise RuntimeError(f"No usable sources found for {topic.title}.")
        evidence = "\n".join(f"- {source.title}: {source.snippet} ({source.url})" for source in sources)
        payload = self._llm.generate_structured(
            f"Create a factual research brief about '{topic.title}'. Use only this supplied evidence. Cross-check claims between sources where possible; explicitly identify uncertainty or disagreement. "
            "Return {\"overview\":string,\"key_claims\":[string],\"uncertainty\":string}.\nEvidence:\n" + evidence,
            task="research_synthesis",
        )
        return ResearchBrief(topic_title=topic.title, overview=str(payload.get("overview", "")), key_claims=[str(claim) for claim in payload.get("key_claims", [])], uncertainty=str(payload.get("uncertainty", "")), sources=sources)
