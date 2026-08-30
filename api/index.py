import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "search_terms.json").read_text(encoding="utf-8"))
TED_URL = "https://api.ted.europa.eu/v3/notices/search"

app = Flask(__name__)

SEARCHES = [
    'FT ~ "air traffic"',
    'FT ~ "instrument flight procedure"',
    'FT ~ "aeronautical information"',
    'FT ~ "air traffic control"',
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

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATC Tender Intelligence</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#17202a;background:#f5f7fa}
*{box-sizing:border-box}body{margin:0}.wrap{max-width:1400px;margin:auto;padding:28px}
header{background:#111827;color:#fff;border-radius:20px;padding:28px 30px;display:flex;justify-content:space-between;gap:20px;align-items:flex-start;box-shadow:0 10px 30px #0002}
h1{margin:0 0 6px;font-size:30px}header p{margin:0;color:#b9c2d0}.badge{background:#243244;border:1px solid #405065;padding:8px 12px;border-radius:999px;font-size:13px;white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.card{background:#fff;border:1px solid #e3e7ed;border-radius:15px;padding:18px}.label{font-size:12px;color:#687386;text-transform:uppercase;letter-spacing:.06em}.num{font-size:28px;font-weight:750;margin-top:5px}
.toolbar{background:#fff;border:1px solid #e3e7ed;border-radius:15px;padding:14px;display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}input,select,button{font:inherit;border:1px solid #d6dce5;border-radius:10px;padding:10px 12px;background:#fff}input{flex:1;min-width:220px}button{cursor:pointer;background:#111827;color:#fff;border-color:#111827}.secondary{background:#fff;color:#111827}
.notice{background:#fff;border:1px solid #e1e6ed;border-radius:15px;padding:20px;margin:10px 0}.top{display:flex;justify-content:space-between;gap:15px}.title{font-weight:700;font-size:18px;line-height:1.35}.meta{color:#657184;font-size:13px;margin:8px 0}.desc{color:#465160;font-size:14px;line-height:1.5;max-height:65px;overflow:hidden}.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}.tag{font-size:12px;padding:5px 8px;border-radius:999px;background:#eef2f7}.score{font-weight:750;font-size:14px}.open{display:inline-block;margin-top:13px;color:#175cd3;text-decoration:none;font-weight:650}.empty{padding:50px;text-align:center;color:#667085}.small{font-size:12px;color:#7a8595;margin-top:12px}
@media(max-width:800px){.cards{grid-template-columns:repeat(2,1fr)}header{flex-direction:column}.top{flex-direction:column}.wrap{padding:15px}}
</style></head>
<body><div class="wrap">
<header><div><h1>ATC Tender Intelligence</h1><p>Live procurement opportunities across simulation, selection, training, procedure design and AIM.</p></div><div class="badge" id="updated">Loading...</div></header>
<section class="cards"><div class="card"><div class="label">Opportunities</div><div class="num" id="count">–</div></div><div class="card"><div class="label">High priority</div><div class="num" id="high">–</div></div><div class="card"><div class="label">Countries</div><div class="num" id="countries">–</div></div><div class="card"><div class="label">Source</div><div class="num" style="font-size:20px">TED</div></div></section>
<div class="toolbar"><input id="search" placeholder="Search tenders, buyers, countries..."><select id="category"><option>All</option></select><select id="country"><option>All</option></select><select id="score"><option value="15">Relevant</option><option value="30">High priority</option><option value="0">All results</option></select><button onclick="load()">Refresh</button></div>
<div id="results"><div class="empty">Searching procurement notices...</div></div>
<div class="small">Live source: TED Search API. Always verify the original procurement notice before acting on an opportunity.</div>
</div>
<script>
let data=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){
 const cat=document.getElementById('category').value,country=document.getElementById('country').value,min=document.getElementById('score').value;
 document.getElementById('results').innerHTML='<div class="empty">Searching procurement notices...</div>';
 try{const r=await fetch(`/api/tenders?category=${encodeURIComponent(cat)}&country=${encodeURIComponent(country)}&min_score=${min}`);const j=await r.json();data=j.results||[];
 document.getElementById('count').textContent=j.count??data.length;document.getElementById('high').textContent=data.filter(x=>x.score>=30).length;document.getElementById('countries').textContent=(j.countries||[]).length;document.getElementById('updated').textContent='Updated '+new Date(j.updated_at).toLocaleTimeString();
 const cs=document.getElementById('category'),co=document.getElementById('country');
 if(cs.options.length===1)(j.categories||[]).forEach(x=>cs.add(new Option(x,x))); if(co.options.length===1)(j.countries||[]).forEach(x=>co.add(new Option(x,x)));
 render();
 }catch(e){document.getElementById('results').innerHTML='<div class="empty">Could not load tender data. '+esc(e.message)+'</div>';}
}
function render(){const q=document.getElementById('search').value.toLowerCase();let rows=data.filter(x=>JSON.stringify(x).toLowerCase().includes(q));
 document.getElementById('results').innerHTML=rows.length?rows.map(x=>`<article class="notice"><div class="top"><div><div class="title">${esc(x.title||'Untitled notice')}</div><div class="meta">${esc(x.country||'Country unknown')} · ${esc(x.buyer||'Buyer not listed')} · Published ${esc(x.published||'Unknown')}</div></div><div class="score">${esc(x.score)} relevance</div></div><div class="desc">${esc(x.description||'No description supplied.')}</div><div class="tags">${(x.matched_categories||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>${x.deadline?`<div class="meta"><strong>Deadline:</strong> ${esc(x.deadline)}</div>`:''}<a class="open" href="${esc(x.source_url)}" target="_blank" rel="noopener">Open original tender ↗</a></article>`).join(''):'<div class="empty">No matching opportunities found.</div>'}
document.getElementById('search').addEventListener('input',render);load();
</script></body></html>'''


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
                score += 12; hits += 1
            elif term_n in body_n:
                score += 5; hits += 1
        if hits:
            matched.append(category)
            if hits >= 2: score += 5
    for term in CONFIG["intent_terms"]:
        if term.lower() in combined: score += 8
    for term in CONFIG["exclude_terms"]:
        if term.lower() in combined: score -= 4
    return max(score, 0), matched


def search_ted(query):
    payload = {"query": query, "fields": FIELDS, "page": 1, "limit": 100,
               "paginationMode": "PAGE_NUMBER", "scope": "ALL", "onlyLatestVersions": True}
    response = requests.post(TED_URL, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("notices", data.get("results", []))


def normalise_notice(raw):
    title = text_value(raw.get("notice-title") or raw.get("title"))
    description = text_value(raw.get("description-lot") or raw.get("description"))
    score, categories = score_notice(title, description)
    publication = text_value(raw.get("publication-number"))
    return {"id": publication or title, "title": title.strip(), "description": description.strip(),
            "country": text_value(raw.get("buyer-country")), "buyer": text_value(raw.get("buyer-name")),
            "deadline": text_value(raw.get("deadline-receipt-tender-date-lot")),
            "published": text_value(raw.get("publication-date")), "notice_type": text_value(raw.get("notice-type")),
            "cpv": text_value(raw.get("classification-cpv")), "score": score,
            "matched_categories": categories,
            "source_url": f"https://ted.europa.eu/en/notice/{publication}/html" if publication else "",
            "source": "TED"}


@app.get("/")
def dashboard():
    return Response(HTML, mimetype="text/html")


@app.get("/api/tenders")
def tenders():
    category = request.args.get("category", "All")
    country = request.args.get("country", "All")
    try: minimum = int(request.args.get("min_score", "15"))
    except ValueError: minimum = 15
    collected, errors = {}, []
    for query in SEARCHES:
        try:
            for raw in search_ted(query):
                item = normalise_notice(raw)
                if not item["title"] or item["score"] < minimum: continue
                if category != "All" and category not in item["matched_categories"]: continue
                if country != "All" and item["country"] != country: continue
                collected[item["id"]] = item
        except Exception as exc: errors.append(str(exc))
    results = sorted(collected.values(), key=lambda x: (x["score"], x["published"]), reverse=True)
    countries = sorted({x["country"] for x in collected.values() if x["country"]})
    return jsonify({"updated_at": datetime.now(timezone.utc).isoformat(), "source": "TED Search API",
                    "results": results[:250], "count": len(results), "countries": countries,
                    "categories": list(CONFIG["categories"].keys()), "errors": errors})


if __name__ == "__main__":
    app.run(debug=True)
