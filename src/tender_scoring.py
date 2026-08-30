"""Relevance scoring for ATC-related procurement opportunities."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class TenderResult:
    title: str
    description: str = ""
    country: str = ""
    buyer: str = ""
    deadline: str = ""
    source_url: str = ""
    matched_categories: List[str] = field(default_factory=list)
    score: int = 0


def _normalise(text: str) -> str:
    return " ".join((text or "").lower().split())


def score_tender(
    title: str,
    description: str,
    categories: Dict[str, Iterable[str]],
    intent_terms: Iterable[str],
    exclude_terms: Iterable[str],
) -> TenderResult:
    """Score a procurement notice using title/description keyword matches.

    Title matches are weighted more heavily than description matches. A notice
    also needs procurement intent unless its category match is exceptionally
    strong. Exclusion terms reduce noise rather than automatically deleting a
    result, because real notices can contain incidental excluded words.
    """
    title_n = _normalise(title)
    body_n = _normalise(description)
    combined = f"{title_n} {body_n}"

    score = 0
    matched = []

    for category, terms in categories.items():
        category_hits = 0
        for term in terms:
            term_n = _normalise(term)
            if term_n and term_n in title_n:
                score += 12
                category_hits += 1
            elif term_n and term_n in body_n:
                score += 5
                category_hits += 1
        if category_hits:
            matched.append(category)
            if category_hits >= 2:
                score += 5

    intent_hits = sum(1 for term in intent_terms if _normalise(term) in combined)
    score += min(intent_hits * 8, 24)

    exclusion_hits = sum(1 for term in exclude_terms if _normalise(term) in combined)
    score -= exclusion_hits * 4

    score = max(0, score)

    return TenderResult(
        title=title,
        description=description,
        matched_categories=matched,
        score=score,
    )


def rank_tenders(results: Iterable[TenderResult]) -> List[TenderResult]:
    """Return highest relevance first, with category matches as a tiebreaker."""
    return sorted(results, key=lambda r: (r.score, len(r.matched_categories)), reverse=True)
