"""Collect only live ATC-related procurement opportunities from multiple sources."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sources.ted import search_ted
from sources.gets import search_gets
from sources.uk_fts import search_uk_fts
from tender_scoring import score_tender, rank_tenders

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/search_terms.json").read_text(encoding="utf-8"))
OUT = ROOT / "data/tenders.json"


def text_value(value):
    if value is None: return ""
    if isinstance(value, str): return value
    if isinstance(value, dict):
        for key in ("eng", "en", "value", "name"):
            if key in value: return text_value(value[key])
        return " ".join(text_value(v) for v in value.values())
    if isinstance(value, list): return " ".join(text_value(v) for v in value)
    return str(value)


def parse_datetime(value):
    raw=text_value(value).strip()
    for candidate in (raw,raw.replace("Z","+00:00")):
        try:
            dt=datetime.fromisoformat(candidate)
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError: pass
    m=re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}).*?UTC([+-]\d{1,2})(?::(\d{2}))?",raw,re.I)
    if m:
        try:
            local=datetime.strptime(f"{m.group(2)} {m.group(1)}","%d %b %Y %I:%M %p")
            sign=1 if m.group(3).startswith("+") else -1
            offset=timezone(sign*timedelta(hours=abs(int(m.group(3))),minutes=int(m.group(4) or 0)))
            return local.replace(tzinfo=offset).astimezone(timezone.utc)
        except ValueError: pass
    return None


def live(deadline):
    dt=parse_datetime(deadline)
    return dt is not None and dt > datetime.now(timezone.utc)


def add_result(results, seen, title, description, country, buyer, deadline, source_url, source, key):
    if not title or key in seen or not live(deadline): return
    scored=score_tender(title,description,CONFIG["categories"],CONFIG["intent_terms"],CONFIG["exclude_terms"])
    if scored.score < 10: return
    seen.add(key); scored.country=country; scored.buyer=buyer; scored.deadline=deadline; scored.source_url=source_url; scored.source=source; scored.status="LIVE"; results.append(scored)


def main():
    results=[]; seen=set(); errors=[]
    queries=['FT ~ "air traffic"','FT ~ "air traffic control"','FT ~ "instrument flight procedure"','FT ~ "aeronautical information"','FT ~ "air navigation"','FT ~ "air traffic management"']
    for query in queries:
        try:
            for raw in search_ted(query,limit=100):
                publication=text_value(raw.get("publication-number")); title=text_value(raw.get("notice-title") or raw.get("title")).strip(); description=text_value(raw.get("description-lot") or raw.get("description")).strip()
                add_result(results,seen,title,description,text_value(raw.get("buyer-country")),text_value(raw.get("buyer-name")),text_value(raw.get("deadline-receipt-tender-date-lot")),f"https://ted.europa.eu/en/notice/{publication}/html" if publication else "","EU TED",publication or f"TED:{title}")
        except Exception as exc: errors.append(f"TED: {exc}")
    try:
        for raw in search_gets(): add_result(results,seen,text_value(raw.get("title")),text_value(raw.get("description")),text_value(raw.get("country")),text_value(raw.get("buyer")),text_value(raw.get("deadline")),raw.get("source_url",""),"NZ GETS",raw.get("id") or raw.get("source_url") or raw.get("title"))
    except Exception as exc: errors.append(f"NZ GETS: {exc}")
    try:
        for raw in search_uk_fts(): add_result(results,seen,text_value(raw.get("title")),text_value(raw.get("description")),text_value(raw.get("country")),text_value(raw.get("buyer")),text_value(raw.get("deadline")),raw.get("source_url",""),"UK Find a Tender",raw.get("id") or raw.get("source_url") or raw.get("title"))
    except Exception as exc: errors.append(f"UK Find a Tender: {exc}")
    ranked=rank_tenders(results)
    payload={"updated_at":datetime.now(timezone.utc).isoformat(),"live_only":True,"source_count":len({getattr(r,"source","") for r in ranked}),"errors":errors,"results":[r.__dict__ for r in ranked]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")

if __name__ == "__main__": main()
