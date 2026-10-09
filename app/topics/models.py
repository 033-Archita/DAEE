from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TopicCandidate:
    title: str
    summary: str
    category: str
    normalized_id: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> "TopicCandidate":
        return cls(**value)
