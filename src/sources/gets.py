"""NZ Government Electronic Tenders Service RSS adapter."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

import requests

RSS_URL = "https://www.gets.govt.nz/ExternalRSSFeed.htm"


def _text(value: Any) -> str:
    return " ".join((value or "").split())


def _item_text(item: ET.Element, names: List[str]) -> str:
    for child in list(item):
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names:
            return _text(child.text)
    return ""


def _deadline(text: str) -> str:
    patterns = [
        r"(?:close date|closing date|close)\s*[:\-]?\s*([^|;<]+)",
        r"(?:deadline)\s*[:\-]?\s*([^|;<]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _text(match.group(1))
    return ""


def search_gets() -> List[Dict[str, Any]]:
    response = requests.get(RSS_URL, timeout=30, headers={"User-Agent": "ATC-Tender-Tracker/1.0"})
    response.raise_for_status()
    root = ET.fromstring(response.content)
    results = []
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1].lower() != "item":
            continue
        title = _item_text(item, ["title"])
        link = _item_text(item, ["link"])
        description = _item_text(item, ["description", "summary", "content"])
        pub = _item_text(item, ["pubdate", "published", "updated"])
        results.append({
            "id": link or title,
            "title": title,
            "description": description,
            "country": "New Zealand",
            "buyer": "",
            "deadline": _deadline(description),
            "published": pub,
            "notice_type": "",
            "source_url": link,
            "source": "NZ GETS",
        })
    return results
