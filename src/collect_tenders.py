"""Collect and rank ATC-related procurement notices from TED."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sources.ted import search_ted
from tender_scoring import score_tender, rank_tenders

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/search_terms.json").read_text(encoding="utf-8"))
OUT = ROOT / "data/tenders.json"


def text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("eng", "en", "value"):
            if key in value:
                return text_value(value[key])
        return " ".join(text_value(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_value(v) for v in value)
    return str(value)


def main() -> None:
    results = []
    seen = set()
    categories = CONFIG["categories"]

    # Keep TED queries deliberately broad, then use our own relevance model.
    queries = [
        'FT ~ "air traffic"',
        'FT ~ "instrument flight procedure"',
        'FT ~ "aeronautical information"',
    ]

    for query in queries:
        for raw in search_ted(query, limit=100):
            title = text_value(raw.get("notice-title") or raw.get("title")).strip()
            description = text_value(raw.get("description-lot") or raw.get("description")).strip()
            key = text_value(raw.get("publication-number")) or f"{title}|{description}"
            if key in seen or not title:
                continue
            seen.add(key)

            scored = score_tender(
                title,
                description,
                categories,
                CONFIG["intent_terms"],
                CONFIG["exclude_terms"],
            )
            if scored.score < 15:
                continue

            scored.country = text_value(raw.get("buyer-country"))
            scored.buyer = text_value(raw.get("buyer-name"))
            scored.deadline = text_value(raw.get("deadline-receipt-tender-date-lot"))
            publication = text_value(raw.get("publication-number"))
            scored.source_url = (
                f"https://ted.europa.eu/en/notice/{publication}/html" if publication else ""
            )
            results.append(scored)

    ranked = rank_tenders(results)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": 1,
        "results": [r.__dict__ for r in ranked],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
