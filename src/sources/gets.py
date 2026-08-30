"""NZ Government Electronic Tenders Service live current-tender adapter."""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

RSS_URL = "https://www.gets.govt.nz/ExternalRSSFeed.htm"
CURRENT_URL = "https://www.gets.govt.nz/ExternalIndex.htm"
HEADERS = {"User-Agent": "ATC-Tender-Tracker/1.0"}


def _text(value: Any) -> str:
    return " ".join((value or "").split())


def _deadline(text: str) -> str:
    patterns = [
        r"(?:close date|closing date|close|deadline)\s*[:\-]?\s*([^|;<]+)",
        r"(\d{1,2}:\d{2}\s*(?:AM|PM)\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s*\(Pacific/Auckland\s+UTC[+-]\d{1,2}(?::\d{2})?\))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match: return _text(match.group(1))
    return ""


def _rss() -> List[Dict[str, Any]]:
    response = requests.get(RSS_URL, timeout=30, headers=HEADERS)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    results=[]
    for item in root.iter():
        if item.tag.rsplit("}",1)[-1].lower() != "item": continue
        values={}
        for child in list(item): values[child.tag.rsplit("}",1)[-1].lower()] = _text(child.text)
        results.append({"id":values.get("link") or values.get("title"),"title":values.get("title","") ,"description":values.get("description",values.get("summary","")),"country":"New Zealand","buyer":"","deadline":_deadline(values.get("description", "")),"published":values.get("pubdate",values.get("published", "")),"notice_type":"","source_url":values.get("link",""),"source":"NZ GETS"})
    return results


def _current_page() -> List[Dict[str, Any]]:
    response=requests.get(CURRENT_URL,timeout=30,headers=HEADERS); response.raise_for_status(); html=response.text
    rows=re.findall(r"<tr[^>]*>(.*?)</tr>",html,re.I|re.S)
    results=[]
    for row in rows:
        links=re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',row,re.I|re.S)
        if not links: continue
        clean=re.sub(r"<[^>]+>"," ",row); clean=_text(re.sub(r"&nbsp;"," ",clean,flags=re.I))
        title=""
        detail_url=""
        for href,label in links:
            label=_text(re.sub(r"<[^>]+>"," ",label))
            if "ExternalTenderDetails" in href and label:
                title=label; detail_url=href if href.startswith("http") else "https://www.gets.govt.nz/"+href.lstrip("/"); break
        if not title: continue
        deadline=_deadline(clean)
        results.append({"id":detail_url or title,"title":title,"description":clean,"country":"New Zealand","buyer":"","deadline":deadline,"published":"","notice_type":"","source_url":detail_url,"source":"NZ GETS"})
    return results


def search_gets() -> List[Dict[str, Any]]:
    """Read GETS' current-tenders page first, with RSS as a fallback."""
    try:
        current=_current_page()
        if current: return current
    except Exception:
        pass
    return _rss()
