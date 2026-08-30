import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "search_terms.json").read_text(encoding="utf-8"))
SOURCES = json.loads((ROOT / "config" / "source_registry.json").read_text(encoding="utf-8"))
TED_URL = "https://api.ted.europa.eu/v3/notices/search"

app = Flask(__name__)
SEARCHES = [
    'FT ~ "air traffic"',
    'FT ~ "air traffic control"',
    'FT ~ "instrument flight procedure"',
    'FT ~ "aeronautical information"',
    'FT ~ "air navigation"',
    'FT ~ "air traffic management"',
]
FIELDS = [
    "publication-number", "notice-title", "description-lot", "buyer-name",
    "buyer-country", "deadline-receipt-tender-date-lot", "publication-date",
    "notice-type", "classification-cpv"
]


def text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("eng", "en", "value", "name"):
            if key in value:
                return text_value(value[key])
        return " ".join(text_value(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_value(v) for v in value)
    return str(value)


def parse_datetime(value):
    if not value:
        return None
    raw = text_value(value).strip()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    match = re.search(
        r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}).*?UTC([+-]\d{1,2})(?::(\d{2}))?",
        raw,
        re.I,
    )
    if match:
        try:
            local = datetime.strptime(
                f"{match.group(2)} {match.group(1)}", "%d %b %Y %I:%M %p"
            )
            sign = 1 if match.group(3).startswith("+") else -1
            offset = timezone(
                sign * timedelta(
                    hours=abs(int(match.group(3))), minutes=int(match.group(4) or 0)
                )
            )
            return local.replace(tzinfo=offset).astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def is_live(item):
    deadline = parse_datetime(item.get("deadline"))
    return deadline is not None and deadline > datetime.now(timezone.utc)


def score_notice(title, description):
    title_n = text_value(title).lower()
    body_n = text_value(description).lower()
    combined = f"{title_n} {body_n}"
    score, matched = 0, []
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


def enrich(raw, source):
    title = text_value(raw.get("notice-title") or raw.get("title"))
    description = text_value(raw.get("description-lot") or raw.get("description"))
    score, categories = score_notice(title, description)
    publication = text_value(raw.get("publication-number"))
    return {
        "id": raw.get("id") or publication or title,
        "title": title.strip(),
        "description": description.strip(),
        "country": text_value(raw.get("buyer-country") or raw.get("country")),
        "buyer": text_value(raw.get("buyer-name") or raw.get("buyer")),
        "deadline": text_value(raw.get("deadline-receipt-tender-date-lot") or raw.get("deadline")),
        "published": text_value(raw.get("publication-date") or raw.get("published")),
        "notice_type": text_value(raw.get("notice-type")),
        "cpv": text_value(raw.get("classification-cpv")),
        "score": score,
        "matched_categories": categories,
        "source_url": raw.get("source_url") or (
            f"https://ted.europa.eu/en/notice/{publication}/html" if publication else ""
        ),
        "source": source,
        "status": "LIVE",
    }


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
    response = requests.post(TED_URL, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("notices", data.get("results", []))


def collect_ted():
    collected, errors = {}, []
    for query in SEARCHES:
        try:
            for raw in search_ted(query):
                item = enrich(raw, "EU TED")
                if item["title"] and item["score"] >= 15 and is_live(item):
                    collected[item["id"]] = item
        except Exception as exc:
            errors.append(f"TED: {exc}")
    return collected, errors


def collect_gets():
    collected, errors = {}, []
    try:
        from src.sources.gets import search_gets
        for raw in search_gets():
            item = enrich(raw, "NZ GETS")
            if item["title"] and item["score"] >= 10 and is_live(item):
                collected[item["id"]] = item
    except Exception as exc:
        errors.append(f"NZ GETS: {exc}")
    return collected, errors


def collect_uk_fts():
    collected, errors = {}, []
    try:
        from src.sources.uk_fts import search_uk_fts
        for raw in search_uk_fts():
            item = enrich(raw, "UK Find a Tender")
            if item["title"] and item["score"] >= 10 and is_live(item):
                collected[item["id"]] = item
    except Exception as exc:
        errors.append(f"UK Find a Tender: {exc}")
    return collected, errors


def collect_all():
    collected, errors = {}, []
    for collector in (collect_ted, collect_gets, collect_uk_fts):
        items, source_errors = collector()
        errors.extend(source_errors)
        for key, item in items.items():
            if key not in collected or item["score"] > collected[key]["score"]:
                collected[key] = item
    return list(collected.values()), errors


@app.get("/")
def dashboard():
    # Serve the dashboard directly from the Python function. This avoids relying
    # on Vercel's static-file routing to resolve /index.html after a redirect.
    return send_file(ROOT / "index.html")


@app.get("/api/tenders")
def tenders():
    category = request.args.get("category", "All")
    country = request.args.get("country", "All")
    source = request.args.get("source", "All")
    try:
        minimum = int(request.args.get("min_score", "10"))
    except ValueError:
        minimum = 10

    results, errors = collect_all()
    results = [
        x for x in results
        if x["score"] >= minimum
        and (category == "All" or category in x["matched_categories"])
        and (country == "All" or country == x["country"])
        and (source == "All" or source == x["source"])
        and is_live(x)
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    countries = sorted({x["country"] for x in results if x["country"]})
    sources = sorted({x["source"] for x in results if x["source"]})
    return jsonify({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "live_only": True,
        "source_count": len(sources),
        "results": results[:250],
        "count": len(results),
        "countries": countries,
        "sources": sources,
        "categories": list(CONFIG["categories"].keys()),
        "source_registry": SOURCES,
        "errors": errors,
    })


if __name__ == "__main__":
    app.run(debug=True)
