"""Turn source-grounded briefs into structured, editorial curiosity stories."""

from __future__ import annotations

from typing import Any

from app.llm.router import LLMRouter
from app.research.models import ResearchBrief, Source
from app.story.models import CuriosityStory
from app.topics.models import TopicCandidate


class StoryGenerator:
    def __init__(self, llm: LLMRouter) -> None:
        self._llm = llm

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.replace("\n", " ").split())

    @staticmethod
    def _normalize_sections(payload: dict[str, Any]) -> list[dict[str, str]]:
        sections: list[dict[str, str]] = []
        for item in payload.get("sections") or []:
            if not isinstance(item, dict):
                continue
            heading = str(item.get("heading") or "").strip()
            content = str(item.get("content") or item.get("body") or item.get("text") or "").strip()
            if heading and content:
                sections.append({"heading": heading, "content": content})
        return sections

    @staticmethod
    def _normalize_sources(payload: dict[str, Any]) -> list[Source]:
        sources: list[Source] = []
        for item in payload.get("sources") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if title and url:
                sources.append(Source(title=title, url=url, snippet=""))
        return sources

    def generate(self, topic: TopicCandidate, research: ResearchBrief) -> CuriosityStory:
        claims = "\n".join(f"- {claim}" for claim in research.key_claims)
        prompt = (
            "Write an editorial curiosity article about the topic below for a general reader who wants something genuinely educational. "
            "Use a structure that fits the subject matter rather than forcing a generic template. "
            "Target 300-450 words, with an absolute minimum of 250 and a hard maximum of 550. "
            "Include a clear title, a hook, at least 2 short sections with informative headings, a concrete example or demonstration, the surprising or counterintuitive idea, why it matters, and a concise takeaway. "
            "Avoid generic encyclopedia prose, Wikipedia-style summaries, hollow adjectives, filler, or unsupported claims. "
            "Do not repeat the title in the opening sentence. Do not invent statistics or sources. Use only the provided research notes. "
            "Return valid JSON only with this shape: {\"title\": string, \"hook\": string, \"sections\": [{\"heading\": string, \"content\": string}], \"takeaway\": string, \"sources\": [{\"title\": string, \"url\": string}]}\n"
            f"Topic: {topic.title}\nCategory: {topic.category}\nOverview: {research.overview}\nClaims:\n{claims}\nUncertainty: {research.uncertainty}"
        )

        try:
            payload = self._llm.generate_structured(prompt, task="story_generation")
            if not isinstance(payload, dict):
                raise ValueError("Story payload was not a JSON object.")

            title = str(payload.get("title") or "").strip()
            hook = str(payload.get("hook") or "").strip()
            sections = self._normalize_sections(payload)
            takeaway = str(payload.get("takeaway") or "").strip()
            if not title or not hook or not takeaway or not sections:
                raise ValueError("Story payload was missing required editorial fields.")

            body_text = "\n\n".join(section["content"] for section in sections)
            if self._word_count(body_text) < 250:
                raise ValueError("Generated story was too short.")

            final_sources = self._normalize_sources(payload)
            if not final_sources:
                final_sources = research.sources
            return CuriosityStory(
                title=title,
                category=topic.category,
                body=body_text,
                hook=hook,
                sections=sections,
                takeaway=takeaway,
                sources=final_sources,
            )
        except Exception:
            response = self._llm.generate(prompt, task="story_generation")
            body = response.text.strip()
            hook = body.split("\n\n")[0].strip() if body else "A small question with a surprisingly large payoff."
            sections = [{"heading": "What to know", "content": body or "The idea is simple but revealing."}]
            takeaway = research.key_claims[-1] if research.key_claims else "A small idea can change how you notice the world."
            title = topic.title.strip() or "A curious idea worth understanding"
            return CuriosityStory(
                title=title,
                category=topic.category,
                body=body,
                hook=hook,
                sections=sections,
                takeaway=takeaway,
                sources=research.sources,
            )
