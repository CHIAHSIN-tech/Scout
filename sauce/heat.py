"""辣度五層。**不得塌成一個數字。**

    python -m sauce.heat --home .evdb --rules heat-1        # L1 上界 ＋ L3 宣稱
    python -m sauce.heatrank --home .evdb --rules heat-rank-1   # L2 聚合排序

## 為什麼不給一個 `heat_shu`

客觀方法是存在的（AOAC 995.03、ASTA 21.3 都是 HPLC 測 capsaicinoid），
但**成品辣醬幾乎沒人公開送驗結果**，而且同一個品種的辣度本身就會變
（NMSU：低辣品種受田間逆境會變辣）。

所以挑一個數字填進去比留空更糟——**它看起來像事實**。五層並存：

- **L0 實測** `shu_lab`：真的送過驗的。覆蓋率 <1%。
- **L1 上界** `heat_ceiling_shu`：宣告的辣椒裡最辣那個品種的文獻上限。
  **只能否證，不能證實**：「絕對不超過 X」是可靠的查詢，「就是 X」不是。
  有辣椒萃取物（oleoresin／capsaicin extract）時上界是 `unbounded`——
  萃取物可以把任何東西拉到任意辣度。
- **L2 排序** `heat_rank`：由排序事實（Hot Ones 棒次、零售商分級、品牌線內順序）聚出來。
- **L3 宣稱** `heat_shu_claims[]`：誰說了多少。**不客觀，但「誰宣稱」本身是事實**，
  而且互相矛盾的宣稱全部保留。
- **L4 標籤** `heat_band_label`：標籤上印的 mild／medium／hot。**只在品牌內可比。**

儀表板篩選用 L1，排序用 L2 的 rank 加信賴區間。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath
from evdb.spool import Spool
from evdb.store import Store

from . import contract
from .composition import RULES_VERSION as COMP_RULES_VERSION
from .names import fold

RULES_VERSION = "heat-1"
PEPPER_SHU = Path(__file__).resolve().parent.parent / "fixtures" / "sauce" / "pepper-shu.csv"

#: 萃取物出現時，上界沒有意義——它可以把任何東西拉到任意辣度。
UNBOUNDED = "unbounded"

#: 標籤上的辣度帶。只在品牌內可比：A 牌的 hot 跟 B 牌的 hot 不是同一件事。
BANDS = ("mild", "medium", "hot", "extra hot", "xxx", "extreme", "insanity")

_SHU_CLAIM = re.compile(
    r"([\d][\d,\.]{2,})\s*(?:\+)?\s*(?:shu|scoville)", re.I)


def pepper_ceilings(path: Path | None = None) -> dict[str, int]:
    p = Path(path or PEPPER_SHU)
    if not p.exists():
        return {}
    out: dict[str, int] = {}
    with p.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = fold(row.get("pepper", ""))
            try:
                out[name] = int(row.get("shu_max") or 0)
            except (TypeError, ValueError):
                continue
    return out


def ceiling_for(peppers: list[str], has_extract: bool,
                table: dict[str, int] | None = None) -> tuple[Any, list[str]]:
    """(上界, 對上的品種)。有萃取物就是 unbounded；一個品種都對不上就留空。

    **留空不是 0。** 0 的意思是「不辣」，留空的意思是「我們不知道」——
    兩者在欄位上長得一樣，但一個是事實、一個是缺口。
    """
    if has_extract:
        return UNBOUNDED, []
    table = pepper_ceilings() if table is None else table
    hits: list[tuple[int, str]] = []
    for raw in peppers or []:
        folded = fold(raw)
        for name, shu in table.items():
            if name and (name == folded or f"-{name}-" in f"-{folded}-"
                         or folded.endswith(f"-{name}") or folded.startswith(f"{name}-")):
                hits.append((shu, name))
    if not hits:
        return "", []
    best = max(hits)
    return best[0], sorted({n for _, n in hits})


def band_label(text: str) -> str:
    low = f" {str(text or '').lower()} "
    for band in reversed(BANDS):        # 從最辣的往回找，"extra hot" 要先於 "hot"
        if f" {band} " in low:
            return band
    return ""


def claims_in(text: str, source: str, observed_at: str) -> list[dict[str, Any]]:
    """文字裡的 SHU 宣稱。多筆並存，各自帶出處——**不合併、不取平均**。"""
    out = []
    for m in _SHU_CLAIM.finditer(str(text or "")):
        raw = m.group(1)
        try:
            value = int(raw.replace(",", "").split(".")[0])
        except ValueError:
            continue
        if 0 < value <= 20_000_000:
            out.append({"shu": value, "raw": m.group(0).strip(), "source": source,
                        "observed_at": observed_at})
    return out


def derive(events: list[Event], rules_version: str = RULES_VERSION) -> list[dict[str, Any]]:
    table = pepper_ceilings()
    comp: dict[str, dict[str, Any]] = {}
    for ev in events:
        # **只收當前規則版本的成分事件。** 舊版的事件永遠留在庫裡（只追加），
        # 而視圖是照版本篩過的——這裡不篩的話，上界會從一筆視圖上根本看不到的
        # 舊成分算出來，於是 `peppers` 是空的、`heat_ceiling_shu` 卻有數字。
        # 那個數字沒有任何一欄解釋得了它從哪來（A45 就是這樣紅的）。
        if (ev.event_type == contract.EV_COMPOSITION
                and str(ev.payload.get("comp_rules_version") or "") == COMP_RULES_VERSION):
            comp[ev.entity_id] = ev.payload

    obs_to_sauce: dict[str, str] = {}
    titles: dict[str, list[tuple[str, str]]] = {}
    for ev in events:
        if ev.event_type != contract.LINK_EVENT:
            continue
        if ev.payload.get("matcher_version") != contract.MATCHER_VERSION:
            continue
        for r in ev.related:
            if r["role"] == "observation":
                obs_to_sauce[r["entity_id"]] = ev.entity_id
    for ev in events:
        if ev.event_type in (contract.EV_PRODUCT, contract.EV_MENTION):
            sid = obs_to_sauce.get(ev.entity_id)
            if sid:
                text = " ".join(str(ev.payload.get(k) or "")
                                for k in ("title", "name", "product_type", "tags"))
                titles.setdefault(sid, []).append((ev.source, text))

    rows: list[dict[str, Any]] = []
    observed_at = now_iso()
    for sid in sorted(set(comp) | set(titles)):
        fields = comp.get(sid, {})
        peppers = fields.get("peppers") or []
        has_extract = bool(fields.get("has_capsaicin_extract"))
        ceiling, matched = ceiling_for(peppers, has_extract, table)

        claims: list[dict[str, Any]] = []
        bands: list[str] = []
        for source, text in titles.get(sid, []):
            claims.extend(claims_in(text, source, observed_at))
            band = band_label(text)
            if band:
                bands.append(band)
        claims.extend(claims_in(fields.get("ingredient_list_raw", ""), "label_photo",
                                observed_at))

        values = sorted({c["shu"] for c in claims})
        rows.append({
            "entity_id": sid,
            "shu_lab": "", "capsaicinoid_ppm": "", "lab_method": "", "tested_on": "",
            "coa_url": "",
            "heat_ceiling_shu": ceiling,
            "heat_ceiling_basis": "|".join(matched),
            "has_capsaicin_extract": has_extract,
            "pepper_ordinal": fields.get("pepper_ordinal", ""),
            "heat_shu_claims": claims,
            "heat_shu_claim_count": len(claims),
            "heat_shu_disagreement": (f"{values[0]}..{values[-1]}"
                                      if len(values) > 1 else ""),
            "heat_band_label": bands[0] if bands else "",
            "brand_line_rank": "",
            "heat_rules_version": rules_version,
        })
    return rows


def to_event(row: dict[str, Any], observed_at: str) -> Event:
    return Event(
        entity_type="sauce_heat", entity_id=row["entity_id"],
        event_type=contract.EV_HEAT_CLAIM, observed_at=observed_at, source="evdb",
        source_record_id=row["entity_id"], ingest_path=IngestPath.BULK.value, payload=row)


def run(home: Home, rules_version: str = RULES_VERSION) -> dict[str, Any]:
    with Store(home, read_only=True) as store:
        events = store.all_events()
    rows = derive(events, rules_version)
    observed_at = now_iso()
    Spool(home, tag="sauce-heat").write([to_event(r, observed_at) for r in rows])
    with_ceiling = sum(1 for r in rows if r["heat_ceiling_shu"] not in ("", None))
    return {"rows": len(rows), "with_ceiling": with_ceiling,
            "unbounded": sum(1 for r in rows if r["heat_ceiling_shu"] == UNBOUNDED),
            "with_claims": sum(1 for r in rows if r["heat_shu_claim_count"]),
            "with_disagreement": sum(1 for r in rows if r["heat_shu_disagreement"]),
            "rules_version": rules_version}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sauce.heat")
    ap.add_argument("--home", default=None)
    ap.add_argument("--rules", default=RULES_VERSION)
    ns = ap.parse_args(argv)
    print(json.dumps(run(Home.resolve(ns.home), ns.rules), ensure_ascii=False, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
