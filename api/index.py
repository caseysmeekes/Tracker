import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "search_terms.json").read_text(encoding="utf-8"))
TED_URL = "https://api.ted.europa.eu/v3/notices/search"

app = Flask(__name__)

SEARCHES = [
    'FT ~ "air traffic"',
    'FT ~ "instrument flight procedure"',
    'FT ~ "aeronautical information"',
]
FIELDS = [
    "publication-number",
    "notice-title",
    "description-lot",
    "buyer-name",
    "buyer-country",
    "deadline-receipt-tender-date-lot",
    "publication-date",
    "notice-type",
    "classification-cpv",
]


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


def score_notice(title, description):
    title_n = text_value(title).lower()
    body_n = text_value(description).lower()
    combined = f"{title_n} {body_n}"
    score = 0
    matched = []

    for category, terms in CONFIG["categories"].items():
        hits = 0
        for term in terms:
            term_n = term.lower()
            if term_n in title_n:
                score += 12
                hits += 1
            elif term_n in body_n:
                score += 5
                hits += 1
        if hits:
            matched.append(category)
            if hits >= 2:
                score += 5

    for term in CONFIG["intent_terms"]:
        if term.lower() in combined:
            score += 8

    for term in CONFIG["exclude_terms"]:
        if term.lower() in combined:
            score -= 4

    return max(score, 0), matched


def search_ted(query):
    payload = {
        "query": query,
        "fields": FIELDS,
        "page": 1,
        "limit": 100,
        "paginationMode": "PAGE_NUMBER",
        "scope": "ALL",
        "onlyLatestVersions": True,
    }
    response = requests.post(TED_URL, json=payload, timeout=12)
    response.raise_for_status()
    data = response.json()
    return data.get("notices", data.get("results", []))


def normalise_notice(raw):
    title = text_value(raw.get("notice-title") or raw.get("title"))
    description = text_value(raw.get("description-lot") or raw.get("description"))
    score, categories = score_notice(title, description)
    publication = text_value(raw.get("publication-number"))
    return {
        "id": publication or title,
        "title": title.strip(),
        "description": description.strip(),
        "country": text_value(raw.get("buyer-country")),
        "buyer": text_value(raw.get("buyer-name")),
        "deadline": text_value(raw.get("deadline-receipt-tender-date-lot")),
        "published": text_value(raw.get("publication-date")),
        "notice_type": text_value(raw.get("notice-type")),
        "cpv": text_value(raw.get("classification-cpv")),
        "score": score,
        "matched_categories": categories,
        "source_url": f"https://ted.europa.eu/en/notice/{publication}/html" if publication else "",
        "source": "TED",
    }


@app.get("/")
def health():
    return jsonify({"ok": True, "service": "ATC Tender Tracker API"})


@app.get("/api/tenders")
def tenders():
    category = request.args.get("category", "All")
    country = request.args.get("country", "All")
    minimum = int(request.args.get("min_score", "15"))

    collected = {}
    errors = []
    for query in SEARCHES:
        try:
            for raw in search_ted(query):
                item = normalise_notice(raw)
                if not item["title"] or item["score"] < minimum:
                    continue
                if category != "All" and category not in item["matched_categories"]:
                    continue
                if country != "All" and item["country"] != country:
                    continue
                collected[item["id"]] = item
        except Exception as exc:
            errors.append(str(exc))

    results = sorted(collected.values(), key=lambda x: (x["score"], x["published"]), reverse=True)
    countries = sorted({x["country"] for x in collected.values() if x["country"]})
    categories = list(CONFIG["categories"].keys())

    return jsonify({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "TED Search API",
        "results": results[:250],
        "count": len(results),
        "countries": countries,
        "categories": categories,
        "errors": errors,
    })


if __name__ == "__main__":
    app.run(debug=True)
