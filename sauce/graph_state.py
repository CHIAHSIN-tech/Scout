"""產生 `state/graph-state-sauce.json`：圖執行的狀態，只放指標不放產物。

    python -m sauce.graph_state --home .evdb --run-id <id> --snapshot <id>

**state 只放路由需要的判斷值與指向產物的指標**——路徑、id、雜湊、筆數；
絕不放產物本身（不放評論正文、不放抓回來的 HTML、不放視圖的列）。
那不是潔癖：state 是每個節點都會讀寫的檔，把產物放進去會讓它變成第二份資料庫，
而且是沒有任何檢查在管的那一份。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home, now_iso
from evdb.store import Store

from . import contract, outlets, storefronts

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "state" / "graph-state-sauce.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def collect(home: Home, run_id: str, snapshot_id: str, rules: str = "v1") -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        stats = store.stats()

    sources = []
    for manifest in sorted((REPO / "state").glob("snapshot-*/MANIFEST.json")):
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        sources.append({"snapshot_path": str(manifest.parent.relative_to(REPO)),
                        "files": doc.get("files"), "sha256": _sha256(manifest),
                        "sources": doc.get("sources", [])})

    views = {}
    for name in ("sauce_views_build", "sauce_views_reviews"):
        path = home.views / name / rules / "manifest.json"
        if path.exists():
            doc = json.loads(path.read_text(encoding="utf-8"))
            views[name] = {"rows": doc.get("rows"), "rows_sha256": doc.get("rows_sha256"),
                           "events_in": doc.get("events_in")}

    return {
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "generated_at": now_iso(),
        "contract": contract.as_dict(),
        "nodes": {
            "N1": {"status": "done", "counts": {}, "note": "契約凍結；docs/sauce-recon.md"},
            "N2": {"status": "done",
                   "counts": {"outlets_whitelisted": len(outlets.load()),
                              "storefronts": len(storefronts.load())}},
            "N3a": {"status": "done", "counts": {"fdc": stats["by_source"].get("fdc", 0),
                                                 "off": stats["by_source"].get("off", 0)}},
            "N3b": {"status": "done",
                    "counts": {"shopify": stats["by_source"].get("shopify", 0),
                               "woo": stats["by_source"].get("woo", 0)}},
            "N3c": {"status": "done",
                    "counts": {"wikipedia": stats["by_source"].get("wikipedia", 0),
                               "awards": stats["by_source"].get("awards", 0),
                               "hotones": stats["by_source"].get("hotones", 0),
                               "wikidata": 0, "reddit": 0}},
            "N3d": {"status": "done",
                    "counts": {"outlet_web": stats["by_source"].get("outlet_web", 0)}},
            "N4": {"status": "done",
                   "counts": {"parsed": stats["by_event_type"].get(contract.EV_PARSED, 0),
                              "verdicts": stats["by_event_type"].get(contract.EV_VERDICT, 0)}},
            "N5": {"status": "done", "counts": {"views": views}},
            "N6": {"status": "done", "counts": {}},
            "N7": {"status": "done", "counts": {}},
        },
        "sources": sources,
        "store": {"events": stats["events"], "entities": stats["entities"],
                  "by_source": stats["by_source"], "by_event_type": stats["by_event_type"]},
        "views": views,
        "artifacts": {
            "acceptance": "ACCEPTANCE-sauce-corpus.md",
            "decisions": "DECISIONS-sauce-corpus.md",
            "known_issues": "KNOWN_ISSUES-sauce-corpus.md",
            "runbook": "RUNBOOK-sauce-refresh.md",
            "recon": "docs/sauce-recon.md",
            "coverage_report": "reports/sauce-coverage.md",
            "reviews_report": "reports/sauce-reviews.md",
            "catalog_csv": "sauce/out/sauce_catalog-v1.csv",
            "reviews_csv": "sauce/out/sauce_reviews-v1.csv",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.graph_state")
    ap.add_argument("--home", default=None)
    ap.add_argument("--run-id", default="run-1")
    ap.add_argument("--snapshot", default="")
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    doc = collect(Home.resolve(ns.home), ns.run_id, ns.snapshot, ns.rules)
    path = Path(ns.out or STATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({"written": str(path), "events": doc["store"]["events"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
