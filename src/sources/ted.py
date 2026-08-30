"""TED Search API adapter.

TED's published-notice Search API is publicly searchable without an API key.
See https://docs.ted.europa.eu/api/latest/search.html
"""

from typing import Any, Dict, List
import requests

BASE_URL = "https://api.ted.europa.eu/v3/notices/search"


def search_ted(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    payload = {
        "query": query,
        "fields": [
            "publication-number",
            "notice-title",
            "description-lot",
            "buyer-name",
            "buyer-country",
            "deadline-receipt-tender-date-lot",
            "publication-date",
            "notice-type",
            "procedure-type",
            "classification-cpv",
        ],
        "limit": min(limit, 250),
        "page": 1,
        "paginationMode": "PAGE_NUMBER",
    }
    response = requests.post(BASE_URL, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    return data.get("notices", data.get("results", []))
