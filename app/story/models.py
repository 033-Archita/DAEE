from __future__ import annotations

from dataclasses import dataclass, field

from app.research.models import Source


@dataclass(frozen=True)
class CuriosityStory:
    title: str
    category: str
    body: str
    takeaway: str
    sources: list[Source]
    hook: str | None = None
    sections: list[dict[str, str]] = field(default_factory=list)

    def sectioned_body(self) -> list[dict[str, str]]:
        if self.sections:
            return self.sections
        if not self.body.strip():
            return []
        paragraphs = [part.strip() for part in self.body.split("\n\n") if part.strip()]
        if not paragraphs:
            return []
        return [{"heading": "What to know", "content": "\n\n".join(paragraphs)}]
