"""UK Find a Tender public OCDS adapter."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

BASE_URL = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("name", "value", "en"):
            if key in value:
                return _text(value[key])
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return str(value)


def search_uk_fts(days: int = 45, limit: int = 100) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    params = {
        "limit": min(limit, 100),
        "stages": "tender",
        "updatedFrom": (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S"),
        "updatedTo": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
        headers={"Accept": "application/json", "User-Agent": "ATC-Tender-Tracker/1.0"},
    )
    response.raise_for_status()
    data = response.json()
    results = []

    for release in data.get("releases", []):
        tender = release.get("tender") or {}
        period = tender.get("tenderPeriod") or {}
        end_date = period.get("endDate") or ""
        if not end_date:
            continue
        buyer = release.get("buyer") or {}
        title = _text(tender.get("title"))
        description = _text(tender.get("description"))
        notice_id = _text(release.get("id"))
        ocid = _text(release.get("ocid"))
        results.append({
            "id": ocid or notice_id or title,
            "title": title,
            "description": description,
            "country": "United Kingdom",
            "buyer": _text(buyer.get("name")),
            "deadline": end_date,
            "published": _text(release.get("date")),
            "notice_type": _text(release.get("tag")),
            "source_url": f"https://www.find-tender.service.gov.uk/procurement/{ocid}" if ocid else "https://www.find-tender.service.gov.uk/Search",
            "source": "UK Find a Tender",
        })

    return results
