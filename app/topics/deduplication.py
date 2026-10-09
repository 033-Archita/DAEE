"""V1 duplicate prevention: stable normalized title identifiers."""

from __future__ import annotations

import re
import unicodedata


def normalize_topic_id(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    # Possessive apostrophes should not create a different identifier from a title without one.
    normalized = normalized.replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def is_duplicate(title: str, known_ids: set[str]) -> bool:
    return normalize_topic_id(title) in known_ids
