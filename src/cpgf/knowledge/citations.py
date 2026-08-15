from __future__ import annotations

from .models import SearchHit


def format_knowledge_citation(hit: SearchHit) -> str:
    page = f", p. {hit.page}" if hit.page is not None else ""
    return f"{hit.citation}{page} [{hit.authority_level.value}]"
