"""把整個領域裝進 store：註冊表 → 抓取 → 載入 → 比對 → 視圖。

    python -m sauce.load --home .evdb --register-only          # 只登記命名空間與來源
    python -m sauce.load --home .evdb --refresh                # 開新快照，全部重抓
    python -m sauce.load --home .evdb --snapshot state/snapshot-<id>   # 重放既有快照
    python -m sauce.load --home .evdb --stage match,views      # 只跑後半段

每一步都只是「再寫一批事件」：重跑不會改寫任何既有事件，內容相同就是同一筆（冪等）。
半年一次的更新就是換一個 `snapshot_id` 再跑一次，舊事件一筆都不會動（A7）。

FDC 走 bulk 匯入（有中間檔，要驗守恆），其餘走 SDK spool（沒有中間檔）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evdb.derive import derive
from evdb.home import Home, now_iso
from evdb.ingest import ingest
from evdb.registry import Registry
from evdb.sdk import Recorder
from evdb.spool import Spool

from . import contract, extract_rules, match, storefronts
from .harvest import STATE, Snapshot, new_snapshot_id
from .net import Fetcher
from .outlets import load as load_outlets
from .sources import awards, fdc, hotones, off, off_image, outlet_web, reddit, shopify, \
    webshop, wikidata, wikipedia, woo

MAPPINGS = Path(__file__).resolve().parent / "mappings"
STAGES = ("register", "harvest", "ingest", "extract_rules", "match", "views")
HARVEST_SOURCES = ("fdc", "off", "shopify", "woo", "webshop", "wikipedia", "wikidata", "awards",
                   "hotones", "reddit", "outlet_web", "off_image")


def register(home: Home) -> dict[str, Any]:
    """命名空間與來源白名單。沒登記過的前綴會被 `evdb validate` 擋下（A2）。"""
    reg = Registry(home.ensure())
    for prefix, desc in contract.NAMESPACES.items():
        reg.add_namespace(prefix, desc)
    for source, desc in contract.SOURCES.items():
        reg.add_source(source, desc)
    return {"namespaces": sorted(reg.namespaces), "sources": sorted(reg.sources)}


def _review_plan(limit_per_outlet: int | None = None) -> list[tuple[dict[str, str], list[str]]]:
    """白名單 × 該站的候選文章網址（由 `sauce.admit` 走 sitemap 找出來的那份）。"""
    evidence_path = Path(__file__).resolve().parent.parent / "fixtures" / "sauce" / \
        "outlets-evidence.json"
    urls_by_host: dict[str, list[str]] = {}
    if evidence_path.exists():
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            urls_by_host[r.get("host", "")] = list((r.get("sauce_content") or {}).get("urls") or [])
    plan = []
    for row in load_outlets():
        urls = urls_by_host.get(row["host"], [])
        if limit_per_outlet:
            urls = urls[:limit_per_outlet]
        if urls:
            plan.append((row, urls))
    return plan


def harvest(home: Home, snapshot: Snapshot, only: tuple[str, ...] = HARVEST_SOURCES,
            log: Any = None, limit_per_outlet: int | None = None,
            limit_label_products: int | None = None) -> dict[str, Any]:
    log = log or sys.stdout
    fetcher = Fetcher()
    recorder = Recorder(source="outlet_web", home=home.root, tag="sauce-review")
    observed_at = now_iso()
    summary: dict[str, Any] = {"snapshot_id": snapshot.id, "sources": {}}

    def spool(tag: str, events: list[Any]) -> int:
        return Spool(home, tag=tag).write(events) if events else 0

    if "fdc" in only:
        # v3：FDC 改走 spool 而不是 bulk CSV——payload 有巢狀的 nutrients 子物件（A10），
        # 而 bulk 的 CSV 只能放平的字串。守恆的帳改由 candidates.csv 記，A5 照樣驗得到。
        got = fdc.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["fdc"] = {
            "candidates": got.get("candidates", 0), "rows_in": got.get("rows_in", 0),
            "kept": got.get("kept", 0), "with_nutrients": got.get("with_nutrients", 0),
            "skipped_category": got.get("skipped_category", 0),
            "skipped_country": got.get("skipped_country", 0),
            "reason": got.get("reason", ""),
            "spooled": spool("sauce-fdc", got.get("events", []))}
        print(f"  fdc {summary['sources']['fdc']}", file=log, flush=True)

    if "off" in only:
        got = off.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["off"] = {"kept": got["kept"],
                                     "spooled": spool("sauce-off", got["events"])}
    if "shopify" in only:
        domains = storefronts.by_platform("shopify")
        got = shopify.harvest_all(fetcher, domains, snapshot, observed_at, log=log)
        summary["sources"]["shopify"] = {"stores": len(domains), "stores_ok": got["stores_ok"],
                                         "kept": got["kept"],
                                         "spooled": spool("sauce-shopify", got["events"])}
    if "woo" in only:
        domains = storefronts.by_platform("woo")
        got = woo.harvest_all(fetcher, domains, snapshot, observed_at, log=log)
        summary["sources"]["woo"] = {"stores": len(domains), "stores_ok": got["stores_ok"],
                                     "kept": got["kept"],
                                     "spooled": spool("sauce-woo", got["events"])}
    if "webshop" in only:
        # 第三條路徑：認不出平台的店。讀不到也要記，見 sources/webshop.py 的模組說明。
        domains = storefronts.by_platform("webshop") + storefronts.by_platform("unknown")
        got = webshop.harvest_all(fetcher, domains, snapshot, observed_at, log=log)
        summary["sources"]["webshop"] = {"stores": got["stores"], "kept": got["kept"],
                                         "unreadable_stores": got["unreadable_stores"],
                                         "spooled": spool("sauce-webshop", got["events"])}
    if "wikipedia" in only:
        got = wikipedia.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["wikipedia"] = {"kept": got["kept"],
                                           "spooled": spool("sauce-wikipedia", got["events"])}
    if "wikidata" in only:
        got = wikidata.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["wikidata"] = {"kept": got["kept"], "reason": got["reason"],
                                          "spooled": spool("sauce-wikidata", got["events"])}
    if "awards" in only:
        got = awards.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["awards"] = {"kept": got["kept"],
                                        "spooled": spool("sauce-awards", got["events"])}
    if "hotones" in only:
        got = hotones.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["hotones"] = {"kept": got["kept"], "seasons": got["seasons"],
                                         "spooled": spool("sauce-hotones", got["events"])}
    if "reddit" in only:
        got = reddit.harvest_all(fetcher, snapshot, observed_at, log=log)
        summary["sources"]["reddit"] = {"kept": got["kept"], "status": got["status"],
                                        "reason": got["reason"]}
    if "off_image" in only:
        image_recorder = Recorder(source="off_image", home=home.root, tag="sauce-label")
        got = off_image.harvest_all(fetcher, image_recorder, snapshot, observed_at,
                                    limit_products=limit_label_products, log=log)
        summary["sources"]["off_image"] = {
            "products": got.get("products", 0), "kept": got["kept"],
            "reasons": got.get("reasons", {}), "reason": got.get("reason", ""),
            "spooled": spool("sauce-label-images", got["events"])}
    if "outlet_web" in only:
        plan = _review_plan(limit_per_outlet)
        got = outlet_web.harvest_all(fetcher, recorder, plan, snapshot, observed_at, log=log)
        summary["sources"]["outlet_web"] = {"outlets": len(plan), "kept": got["kept"],
                                            "spooled": spool("sauce-reviews", got["events"])}

    summary["net"] = dict(fetcher.stats)
    summary["manifest"] = str(snapshot.manifest({"sources": sorted(only)}))
    return summary


def run(home: Home, stages: tuple[str, ...] = STAGES, snapshot_id: str | None = None,
        only: tuple[str, ...] = HARVEST_SOURCES, rules: str = "v1",
        log: Any = None, limit_per_outlet: int | None = None,
        limit_label_products: int | None = None) -> dict[str, Any]:
    log = log or sys.stdout
    out: dict[str, Any] = {}
    if "register" in stages:
        out["register"] = register(home)
    if "harvest" in stages:
        snapshot = Snapshot(snapshot_id or new_snapshot_id())
        out["harvest"] = harvest(home, snapshot, only, log, limit_per_outlet,
                                 limit_label_products)
    if "ingest" in stages:
        out["ingest"] = ingest(home)
    if "extract_rules" in stages:
        from evdb.store import Store
        with Store(home, read_only=True) as store:
            got = extract_rules.run(store.all_events())
        Spool(home, tag="sauce-extract-rules").write(got["events"])
        out["extract_rules"] = {k: v for k, v in got.items() if k != "events"}
        out["ingest_rules"] = ingest(home)
    if "match" in stages:
        out["match"] = match.run(home)
        out["ingest_links"] = ingest(home)
    if "views" in stages:
        out["catalog"] = derive(home, "sauce.views:build", rules)
        out["reviews"] = derive(home, "sauce.views:reviews", rules)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.load")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--register-only", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="開一個新快照，全部重抓")
    ap.add_argument("--snapshot", default=None, help="重放既有快照目錄（state/snapshot-<id>）")
    ap.add_argument("--stage", default=None, help="逗號分隔：register,harvest,ingest,match,views")
    ap.add_argument("--only", default=None, help="逗號分隔的來源清單")
    ap.add_argument("--limit-per-outlet", type=int, default=None)
    ns = ap.parse_args(argv)
    home = Home.resolve(ns.home).ensure()

    stages = STAGES
    if ns.register_only:
        stages = ("register",)
    elif ns.stage:
        stages = tuple(s.strip() for s in ns.stage.split(",") if s.strip())
    elif ns.snapshot and not ns.refresh:
        # 重放既有快照：不重抓，只重新載入與重算
        stages = ("register", "ingest", "extract_rules", "match", "views")

    snapshot_id = None
    if ns.snapshot:
        snapshot_id = Path(ns.snapshot).name.removeprefix("snapshot-")
    only = tuple(s.strip() for s in ns.only.split(",")) if ns.only else HARVEST_SOURCES
    out = run(home, stages, snapshot_id, only, ns.rules, limit_per_outlet=ns.limit_per_outlet)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
