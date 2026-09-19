"""Wikidata：結構化、可列舉、帶跨語言別名的名單來源。

它給的是「這個世界上有哪些辣醬與辣醬品牌」，不是「哪裡買得到」——所以產出一律是
`sauce.observation.mention`（只有名字），可購性留給零售層的觀察去說。

用官方 SPARQL 端點。查兩件事：
- 品項：`P31/P279*` 指到 hot sauce（Q522171）或 chili sauce（Q5098942）的東西；
- 品牌：上面那些品項的製造商（P176）／品牌（P1716）。

SPARQL 端點會限流（429）也會逾時（500）；`sauce.net` 的退避會處理，真的拿不到就標
degraded 往下走——名單來源掛掉不該讓整批停下來。
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher

SOURCE = "wikidata"
ENDPOINT = "https://query.wikidata.org/sparql"

#: hot sauce / chili sauce 這兩個類別，連同它們的子類
ROOTS = ("Q522171", "Q5098942")

QUERY = """
SELECT ?item ?itemLabel ?makerLabel ?brandLabel ?countryLabel WHERE {
  VALUES ?root { %s }
  ?item wdt:P31/wdt:P279* ?root .
  OPTIONAL { ?item wdt:P176 ?maker . }
  OPTIONAL { ?item wdt:P1716 ?brand . }
  OPTIONAL { ?item wdt:P495 ?country . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul" . }
}
LIMIT 3000
""" % " ".join(f"wd:{q}" for q in ROOTS)


def query_url(query: str = QUERY) -> str:
    return f"{ENDPOINT}?query={quote(query)}&format=json"


def to_events(payload: dict[str, Any], observed_at: str) -> list[Event]:
    out: list[Event] = []
    for row in ((payload.get("results") or {}).get("bindings") or []):
        def val(key: str) -> str:
            return str((row.get(key) or {}).get("value") or "").strip()

        item = val("item")
        name = val("itemLabel")
        if not item or not name or name.startswith("Q"):
            continue                       # 只有 QID 沒有標籤的條目不收：那不是名字
        qid = item.rsplit("/", 1)[-1]
        out.append(harvest.mention_event(
            source=SOURCE, key=qid, name=name,
            brand=val("brandLabel") or val("makerLabel"),
            url=item, observed_at=observed_at,
            payload={"qid": qid, "maker": val("makerLabel"),
                     "country_of_origin": val("countryLabel")}))
    return out


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                log: Any = None) -> dict[str, Any]:
    got = fetcher.get(query_url(), accept="application/sparql-results+json")
    if not got.ok:
        return {"source": SOURCE, "events": [], "kept": 0, "reason": got.reason}
    try:
        payload = json.loads(got.body.decode("utf-8", "replace"))
    except ValueError:
        return {"source": SOURCE, "events": [], "kept": 0, "reason": "not_json"}
    snapshot.write(SOURCE, "sparql.json", payload)
    events = to_events(payload, observed_at)
    if log:
        print(f"  wikidata kept={len(events)}", file=log, flush=True)
    return {"source": SOURCE, "events": events, "kept": len(events), "reason": ""}
