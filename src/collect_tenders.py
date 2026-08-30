"""Collect and rank ATC-related procurement notices.

The first live adapter is TED. Additional national procurement adapters can be
added without changing the scoring or dashboard data contract.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from sources.ted import search_ted
from tender_scoring import score_tender, rank_tenders

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/search_terms.json").read_text())
OUT = ROOT / "data/tenders.json"


def main() -> None:
    results = []
    seen = set()
    categories = CONFIG["categories"]

    # Expert queries deliberately combine the domain vocabulary with procurement intent.
    queries = [
        '"air traffic control" AND (simulator OR simulation) AND (tender OR procurement OR "contract notice")',
        '"air traffic controller" AND (selection OR aptitude OR psychometric) AND (tender OR procurement OR RFP)',
        '"air traffic control" AND (training OR trainer) AND (tender OR procurement OR RFP)',
        '"instrument flight procedure" AND (design OR PBN) AND (tender OR procurement OR RFP)',
        '"aeronautical information" AND (management OR service OR AIS OR AIXM) AND (tender OR procurement OR RFP)',
    ]

    for query in queries:
        for raw in search_ted(query):
            title = str(raw.get("notice-title") or raw.get("title") or "").strip()
            description = str(raw.get("description-lot") or raw.get("description") or "").strip()
            key = str(raw.get("publication-number") or raw.get("id") or f"{title}|{description}")
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

            scored.country = str(raw.get("buyer-country") or "")
            scored.buyer = str(raw.get("buyer-name") or "")
            scored.deadline = str(raw.get("deadline-receipt-tender-date-lot") or "")
            publication = str(raw.get("publication-number") or "")
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
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
