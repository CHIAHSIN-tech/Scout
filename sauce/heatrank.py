"""L2：辣度的聚合排序（規則 `heat-rank-1`）。

    python -m sauce.heatrank --home .evdb --rules heat-rank-1

## 為什麼是排序而不是數字

沒有人公開送驗成品辣醬，所以「多辣」這件事只有**相對**的證據：
Hot Ones 每季的棒次是由辣到辣的排序、同一個品牌線內的 mild/medium/hot 是排序、
零售商的分級也是排序。把這些配對比較餵給 Bradley–Terry，得到的是一個
**沒有單位的相對強度**，而不是假裝精確的 SHU。

## 兩條紀律

1. **排序輸入事實 ≥ 2 筆才給 rank。** 只有一筆就留空——
   一筆事實推不出排序，給一個點估計等於無中生有（A46）。
2. **信賴區間只反映輸入的一致程度，不反映輸入的正確性。**
   三個零售商抄同一份廠商資料會得到很窄的區間，而且可能一起錯。
   這一點檢查器擋不住，必須寫進報告（見 spec CHECKLIST 第 7 題）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .heat import BANDS
from .names import fold

RULES_VERSION = "heat-rank-1"
OUT_DIR = Path(__file__).resolve().parent.parent / "state" / "heatrank"

MIN_FACTS = 2          # A46：少於這個數就不給 rank
BOOTSTRAP = 200        # 信賴區間的重抽次數
ITERATIONS = 120       # Bradley–Terry 的迭代上限


def ordering_pairs(events: list[Event]) -> list[tuple[str, str, str]]:
    """(比較辣的, 比較不辣的, 這筆事實從哪來)。**兩邊都必須是真的 sauce entity_id。**

    兩種來源：
    - `sauce.observation.lineup`：棒次越後面越辣，所以 i+1 勝過 i。
    - 品牌線內的辣度帶：同一個品牌裡 hot 勝過 medium 勝過 mild。

    ## 棒次的字串要先變成實體，對不上就丟掉

    棒次事件裡的每一棒只是一行字（`"Los Calientes Rojo"`），不是實體。
    直接拿那行字當鍵會出兩種錯，而且兩種都很難從結果上看出來：

    1. **鍵不是實體**。`sauce.heat.ordering` 會寫出
       `entity_id = "Custom gift box ready to share"` 這種列——那是季號包裡的贈品，
       不是一款醬。evdb 的命名空間體檢（A2）會抓到，但在那之前它已經進了排序。
    2. **同一款醬在不同季用不同寫法**，兩個鍵各自排各自的，看起來像兩款不同的醬。

    所以這裡先用已比對的產品名建一張 `折疊後的名字 → sauce entity_id` 的表，
    對不上的棒次**整對丟掉**——寧可少一筆排序事實，不要多一個假實體。
    """
    pairs: list[tuple[str, str, str]] = []

    obs_to_sauce: dict[str, str] = {}
    brand_of: dict[str, str] = {}
    for ev in events:
        if ev.event_type != contract.LINK_EVENT:
            continue
        if ev.payload.get("matcher_version") != contract.MATCHER_VERSION:
            continue
        for r in ev.related:
            if r["role"] == "observation":
                obs_to_sauce[r["entity_id"]] = ev.entity_id
        brand_of[ev.entity_id] = str(ev.payload.get("brand_key") or "")

    # 折疊後的產品名（含品牌前綴的寫法）→ sauce entity_id
    by_name: dict[str, str] = {}
    for ev in events:
        if ev.event_type != contract.EV_PARSED:
            continue
        sid = obs_to_sauce.get(ev.entity_id)
        if not sid:
            continue
        brand = str(ev.payload.get("brand") or "")
        product = str(ev.payload.get("product") or "")
        for name in (product, f"{brand} {product}"):
            key = fold(name)
            if key:
                by_name.setdefault(key, sid)

    def resolve(text: str) -> str:
        key = fold(text)
        return by_name.get(key, "")

    # --- 棒次 ---
    unresolved = 0
    for ev in events:
        if ev.event_type != contract.EV_LINEUP:
            continue
        items = ev.payload.get("items") or []
        ladder = [resolve(str((i or {}).get("text") or "")) for i in items]
        unresolved += sum(1 for n, i in enumerate(items) if not ladder[n])
        for i in range(len(ladder) - 1):
            if ladder[i] and ladder[i + 1] and ladder[i] != ladder[i + 1]:
                pairs.append((ladder[i + 1], ladder[i], f"lineup:{ev.payload.get('season')}"))
    ordering_pairs.unresolved_lineup_items = unresolved      # type: ignore[attr-defined]

    # --- 品牌線內的辣度帶 ---
    band_rank = {b: n for n, b in enumerate(BANDS)}
    by_brand: dict[str, list[tuple[int, str]]] = {}
    for ev in events:
        if ev.event_type != contract.EV_HEAT_CLAIM:
            continue
        band = str(ev.payload.get("heat_band_label") or "")
        brand = brand_of.get(ev.entity_id, "")
        if band and brand:
            by_brand.setdefault(brand, []).append((band_rank.get(band, 0), ev.entity_id))
    for brand, members in by_brand.items():
        members.sort()
        for i in range(len(members) - 1):
            lo, hi = members[i], members[i + 1]
            if lo[0] < hi[0]:
                pairs.append((hi[1], lo[1], f"brand_line:{brand}"))
    return pairs


def bradley_terry(pairs: list[tuple[str, str, str]],
                  iterations: int = ITERATIONS) -> dict[str, float]:
    """最小可用的 Bradley–Terry（MM 演算法）。回傳每個項目的對數強度。"""
    items = sorted({x for a, b, _ in pairs for x in (a, b)})
    if not items:
        return {}
    strength = {i: 1.0 for i in items}
    wins: dict[str, float] = {i: 0.0 for i in items}
    for a, b, _ in pairs:
        wins[a] += 1.0
    for _ in range(iterations):
        new: dict[str, float] = {}
        for i in items:
            denom = 0.0
            for a, b, _ in pairs:
                if i == a or i == b:
                    denom += 1.0 / (strength[a] + strength[b])
            new[i] = (wins[i] / denom) if denom > 0 else strength[i]
        total = sum(new.values()) or 1.0
        strength = {i: max(v / total * len(items), 1e-9) for i, v in new.items()}
    return {i: math.log(v) for i, v in strength.items()}


def rank_with_ci(pairs: list[tuple[str, str, str]], seed: int = 20260920
                 ) -> dict[str, dict[str, Any]]:
    """點估計 ＋ bootstrap 區間。**種子固定**，否則同一份輸入跑兩次會得到不同區間。"""
    base = bradley_terry(pairs)
    if not base:
        return {}
    order = sorted(base, key=lambda k: -base[k])
    point = {k: n + 1 for n, k in enumerate(order)}

    rng = random.Random(seed)
    samples: dict[str, list[int]] = {k: [] for k in base}
    for _ in range(BOOTSTRAP):
        drawn = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        strength = bradley_terry(drawn, iterations=40)
        if not strength:
            continue
        ordered = sorted(strength, key=lambda k: -strength[k])
        for n, k in enumerate(ordered, start=1):
            samples[k].append(n)
    out: dict[str, dict[str, Any]] = {}
    for key, ranks in samples.items():
        ranks = sorted(ranks)
        if not ranks:
            continue
        lo = ranks[int(0.05 * (len(ranks) - 1))]
        hi = ranks[int(0.95 * (len(ranks) - 1))]
        out[key] = {"heat_rank": point[key], "heat_rank_ci_low": min(lo, point[key]),
                    "heat_rank_ci_high": max(hi, point[key])}
    return out


def run(home: Home, rules_version: str = RULES_VERSION,
        out_dir: Path | None = None) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    pairs = ordering_pairs(events)
    facts: dict[str, int] = {}
    for a, b, _ in pairs:
        facts[a] = facts.get(a, 0) + 1
        facts[b] = facts.get(b, 0) + 1
    ranked = rank_with_ci(pairs)

    rows = []
    for key in sorted(ranked):
        if facts.get(key, 0) < MIN_FACTS:
            continue          # A46：一筆事實不給點估計
        rows.append({"key": key, "facts": facts.get(key, 0), **ranked[key]})

    # 排序也是事實，所以它也是事件——視圖只讀事件，不讀這個模組的輸出檔。
    observed_at = now_iso()
    Spool(home, tag="sauce-heatrank").write([
        Event(entity_type="sauce_heat_rank", entity_id=r["key"],
              event_type=contract.EV_HEAT_ORDER, observed_at=observed_at, source="evdb",
              source_record_id=r["key"], ingest_path=IngestPath.BULK.value,
              payload={**r, "heat_rank_rules_version": rules_version})
        for r in rows])

    out = Path(out_dir or OUT_DIR) / rules_version
    out.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    (out / "heatrank.jsonl").write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sources: dict[str, int] = {}
    for _, _, why in pairs:
        kind = why.split(":", 1)[0]
        sources[kind] = sources.get(kind, 0) + 1
    (out / "manifest.json").write_text(
        json.dumps({"rules_version": rules_version, "rows": len(rows),
                    "pairs": len(pairs), "pair_sources": sources,
                    "rows_sha256": digest}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return {"pairs": len(pairs), "pair_sources": sources, "ranked": len(rows),
            "unresolved_lineup_items": getattr(ordering_pairs,
                                               "unresolved_lineup_items", 0),
            "skipped_too_few_facts": len(ranked) - len(rows),
            "rows_sha256": digest, "path": str(out / "heatrank.jsonl")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.heatrank")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default=RULES_VERSION)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    print(json.dumps(run(Home.resolve(ns.home), ns.rules,
                         Path(ns.out) if ns.out else None),
                     ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
