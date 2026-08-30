"""Tender monitor entry point.

The production adapter can plug public procurement APIs/RSS feeds into
`collect_notices`. The normalisation and scoring layer is deliberately kept
separate so each source can be added without changing the matching logic.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from tender_scoring import TenderResult, rank_tenders, score_tender

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "search_terms.json"
DATA = ROOT / "data" / "tenders.json"


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def collect_notices():
    """Return notices collected from configured procurement adapters.

    This starts empty so the repository never invents tender records. Add
    source adapters here for TED, national procurement portals and other
    public tender feeds as their APIs/RSS interfaces are configured.
    """
    return []


def process(notices):
    config = load_config()
    results = []
    for notice in notices:
        result = score_tender(
            notice.get("title", ""),
            notice.get("description", ""),
            config["categories"],
            config["intent_terms"],
            config["exclude_terms"],
        )
        result.country = notice.get("country", "")
        result.buyer = notice.get("buyer", "")
        result.deadline = notice.get("deadline", "")
        result.source_url = notice.get("source_url", "")
        if result.score >= 20:
            results.append(result)
    return rank_tenders(results)


def serialise(results):
    return [
        {
            "title": r.title,
            "description": r.description,
            "country": r.country,
            "buyer": r.buyer,
            "deadline": r.deadline,
            "source_url": r.source_url,
            "matched_categories": r.matched_categories,
            "score": r.score,
        }
        for r in results
    ]


def main():
    DATA.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "results": serialise(process(collect_notices())),
    }
    DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
