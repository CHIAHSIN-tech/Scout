"""長尾店面的種子名單（`fixtures/sauce/storefronts.csv`）。

長尾之所以是長尾，就是因為沒有一份現成的清單。所以名單是**推導出來的**，不是手打的：

1. 先抓幾間辣醬專賣零售（它們本來就是別人的貨架），把每一筆商品的 `vendor` 收集起來；
2. 每個 vendor 名字折成幾個可能的網域（`xxx.com`、`xxxsauce.com`、`xxxhotsauce.com`…）；
3. 逐一確認它真的是一間 Shopify／WooCommerce 店、而且真的賣辣醬；
4. 確認過的才寫進 `storefronts.csv`，進版控。

猜錯的網域就是猜錯，驗證不過就不寫進去——名單寧可短，不要假。

    python -m sauce.storefronts discover        # 重新推導並覆寫 storefronts.csv
    python -m sauce.storefronts check           # 只檢查現有名單還在
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from evdb.home import now_iso

from .harvest import Snapshot
from .net import Fetcher
from .outlets import FIXTURES
from .sources import filters, shopify, woo

STOREFRONTS = FIXTURES / "storefronts.csv"
COLUMNS = ("domain", "platform", "discovered_via", "verified_on", "sauce_products")

#: 推導的起點：本身就是「別人的貨架」的專賣零售，vendor 欄位等於一份品牌名單。
SEED_RETAILERS: tuple[str, ...] = (
    "heatonist.com", "hotsaucedepot.com", "fuegobox.com", "pepperpalace.com",
    "hotsauce.com", "thehotsaucefactory.com", "sauceshop.co", "chilliwizards.com",
    "hotsaucewilly.com", "hotsauceemporium.com", "sauceathome.com", "hotsauceworld.com",
)

#: 已知的品牌直營店（推導漏掉的、或名字折不出網域的，手動補在這裡）
SEED_BRANDS: tuple[str, ...] = (
    "secretaardvark.com", "yellowbirdsauce.com", "truff.com", "bushwickkitchen.com",
    "queenmajesty.com", "smallaxepeppers.com", "brooklyndelhi.com", "adoboloco.com",
    "torchbearersauces.com", "highriversauces.com", "puckerbuttpeppercompany.com",
    "dawsonshotsauce.com", "hellfirehotsauce.com", "cajohns.com", "melindas.com",
    "bravadospice.com", "karmasauce.com", "luckydoghotsauce.com", "defcansauces.com",
    "heartbeathotsauce.com", "fatcatgourmet.com", "volcanicpeppers.com",
    "mikeshothoney.com", "redclayhotsauce.com", "elyucateco.com", "cholula.com",
    "marieshapsusa.com", "angryirishmansauce.com", "seedranch.com", "hankssauce.com",
)

_SLUG = re.compile(r"[^a-z0-9]+")
#: vendor 名字 → 可能的網域後綴。順序＝命中率。
DOMAIN_SHAPES = ("{s}.com", "{s}sauce.com", "{s}sauces.com", "{s}hotsauce.com",
                 "{s}foods.com", "{s}.co")
MAX_GUESSES_PER_VENDOR = 3


def slug(name: str) -> str:
    return _SLUG.sub("", str(name or "").lower())


def guesses(vendor: str) -> list[str]:
    s = slug(vendor)
    if len(s) < 4 or len(s) > 30:
        return []
    return [shape.format(s=s) for shape in DOMAIN_SHAPES][:MAX_GUESSES_PER_VENDOR]


def _woo_tags(product: dict[str, Any]) -> str:
    return " ".join(str(t.get("name", "")) for t in (product or {}).get("categories") or [])


def _inspect_store(fetcher: Fetcher, domain: str) -> dict[str, Any]:
    """這個網域是不是一間賣辣醬的店。回傳 {platform, sauce_products}；不是就 platform=''。"""
    got = fetcher.get(shopify.products_url(domain, 1), accept="application/json")
    if got.ok:
        try:
            payload = json.loads(got.body.decode("utf-8", "replace"))
        except ValueError:
            payload = None
        if shopify.looks_like_shopify(payload):
            n = sum(1 for p in payload["products"]
                    if filters.keep(p.get("title"), p.get("product_type"), p.get("tags")))
            if n:
                return {"platform": "shopify", "sauce_products": n}
    got = fetcher.get(woo.products_url(domain, 1), accept="application/json")
    if got.ok:
        try:
            payload = json.loads(got.body.decode("utf-8", "replace"))
        except ValueError:
            payload = None
        if isinstance(payload, list) and payload:
            n = sum(1 for p in payload if filters.keep((p or {}).get("name"), "", _woo_tags(p)))
            if n:
                return {"platform": "woo", "sauce_products": n}
    return {"platform": "", "sauce_products": 0}


def domains_from_awards(state_dir: Path | None = None) -> list[str]:
    """得獎名錄裡的公司網址。

    一年一千筆得獎紀錄、每一筆都附著廠商自己的網站——那是一份別的地方拿不到的小廠名冊，
    而且比「用品牌名去猜網域」準得多（猜法的命中率大約一成，這份是直接給網址）。
    """
    from .sources.awards import company_domains, pdf_text

    root = Path(state_dir or Path(__file__).resolve().parent.parent / "state")
    texts: list[str] = []
    for pdf in sorted(root.glob("snapshot-*/awards/*.pdf")):
        texts.append(pdf_text(pdf.read_bytes()))
    return company_domains("\n".join(texts)) if texts else []


def vendors_from(fetcher: Fetcher, retailers: Iterable[str], snapshot: Snapshot,
                 log: Any = None) -> list[str]:
    seen: dict[str, int] = {}
    for domain in retailers:
        got = shopify.harvest_store(fetcher, domain, snapshot, now_iso())
        for ev in got["events"]:
            vendor = str(ev.payload.get("brand") or "").strip()
            if vendor:
                seen[vendor] = seen.get(vendor, 0) + 1
        if log:
            print(f"  seed {domain:<30} products={got['kept']:<5} vendors={len(seen)} "
                  f"{got['reason']}", file=log, flush=True)
    return sorted(seen, key=lambda v: (-seen[v], v))


def discover(out: Path | None = None, log: Any = None,
             snapshot: Snapshot | None = None, max_vendors: int = 400) -> dict[str, Any]:
    fetcher = Fetcher()
    snap = snapshot or Snapshot("storefront-discovery")
    rows: dict[str, dict[str, str]] = {}
    today = now_iso()[:10]

    def add(domain: str, via: str, found: dict[str, Any]) -> None:
        if found["platform"] and domain not in rows:
            rows[domain] = {"domain": domain, "platform": found["platform"],
                            "discovered_via": via, "verified_on": today,
                            "sauce_products": str(found["sauce_products"])}

    for domain in SEED_RETAILERS + SEED_BRANDS:
        add(domain, "seed", _inspect_store(fetcher, domain))
        if log:
            print(f"  seed-verify {domain:<34} {'ok' if domain in rows else '-'}",
                  file=log, flush=True)

    for domain in domains_from_awards():
        if domain in rows:
            continue
        found = _inspect_store(fetcher, domain)
        add(domain, "awards_directory", found)
        if log and domain in rows:
            print(f"  awards {domain:<38} ({found['platform']}, {found['sauce_products']})",
                  file=log, flush=True)

    vendors = vendors_from(fetcher, [d for d in SEED_RETAILERS if d in rows], snap, log)
    for vendor in vendors[:max_vendors]:
        for guess in guesses(vendor):
            if guess in rows:
                break
            found = _inspect_store(fetcher, guess)
            if found["platform"]:
                add(guess, f"vendor:{vendor}", found)
                if log:
                    print(f"  vendor {vendor:<30} -> {guess} ({found['platform']}, "
                          f"{found['sauce_products']})", file=log, flush=True)
                break

    path = Path(out or STOREFRONTS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLUMNS), lineterminator="\n")
        w.writeheader()
        for domain in sorted(rows):
            w.writerow(rows[domain])
    return {"storefronts": len(rows), "vendors_seen": len(vendors),
            "net_stats": fetcher.stats, "path": str(path)}


def load(path: Path | None = None) -> list[dict[str, str]]:
    p = Path(path or STOREFRONTS)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k}
                for r in csv.DictReader(fh)]


def by_platform(platform: str, path: Path | None = None) -> list[str]:
    return [r["domain"] for r in load(path) if r.get("platform") == platform]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.storefronts")
    ap.add_argument("cmd", choices=("discover", "check"))
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    if ns.cmd == "discover":
        out = discover(Path(ns.out) if ns.out else None, log=sys.stdout)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    rows = load()
    print(json.dumps({"storefronts": len(rows),
                      "platforms": sorted({r["platform"] for r in rows})},
                     ensure_ascii=False, indent=1))
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
