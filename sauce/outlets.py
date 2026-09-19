"""評論發布單位的白名單（`fixtures/sauce/outlets.csv`）。

准入是人做的判斷，但**判斷結果是資料**：每一列都要有 `admitted_on` 與 `evidence_url`，
所以半年後重跑時可以逐列檢討，而抓取端在執行時完全不需要判斷「這站專不專業」——
它只認名單（A22）。

准入依據三選一（A21）：
- `masthead`             站上有可查的編輯團隊／編輯政策頁
- `named_author_series`  同一位掛名作者在該站有 ≥10 篇、跨 ≥2 年的辣醬／調味料評論
- `methodology_page`     該站公開說明它怎麼評（誰試、幾款、是否盲測）

`tier` 只是分析時的篩子，不是准入門檻；`conflict_of_interest` 是同一個原則的另一面——
零售商的部落格照收，但把利益衝突寫成欄位，讓分析時可以排除，而不是在收錄階段
替日後的分析先做掉這個決定。
"""
from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlsplit

from .contract import ADMISSION_BASIS, CONFLICT_OF_INTEREST, OUTLET_TIER
from .names import fold

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sauce"
WHITELIST = FIXTURES / "outlets.csv"
CANDIDATES = FIXTURES / "outlets-candidates.csv"

COLUMNS = ("outlet", "domain", "admitted_on", "admission_basis", "evidence_url",
           "tier", "conflict_of_interest")


class OutletNotAdmitted(Exception):
    """要抓的網址不在白名單上。抓取端遇到它就停手——一個位元組都不抓（A22）。"""


def outlet_key(outlet: str) -> str:
    return fold(outlet)


def host_of(url_or_domain: str) -> str:
    """把網址或 `domain` 欄位化成可比對的主機名：去 scheme、去路徑、去 www.、小寫。"""
    s = str(url_or_domain or "").strip().lower()
    if "://" not in s:
        s = "//" + s
    host = urlsplit(s).netloc or urlsplit(s).path.split("/")[0]
    host = host.split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def path_prefix_of(domain_field: str) -> str:
    """`nytimes.com/wirecutter` 這種帶路徑的欄位，路徑部分用來在同一個主機下分辨 outlet。"""
    s = str(domain_field or "").strip().lower()
    s = s.split("://", 1)[-1]
    _, _, rest = s.partition("/")
    return "/" + rest.strip("/") if rest.strip("/") else ""


def _bad(row: dict[str, str], line: int) -> list[str]:
    problems = []
    for col in COLUMNS:
        if col not in row:
            problems.append(f"line {line}: 缺欄位 {col}")
    if row.get("admission_basis") not in ADMISSION_BASIS:
        problems.append(f"line {line}: admission_basis={row.get('admission_basis')!r} 不在允許值內")
    if row.get("tier") not in OUTLET_TIER:
        problems.append(f"line {line}: tier={row.get('tier')!r} 不在允許值內")
    if row.get("conflict_of_interest") not in CONFLICT_OF_INTEREST:
        problems.append(f"line {line}: conflict_of_interest={row.get('conflict_of_interest')!r} 不在允許值內")
    if not (row.get("evidence_url") or "").strip():
        problems.append(f"line {line}: evidence_url 是空的")
    if not (row.get("admitted_on") or "").strip():
        problems.append(f"line {line}: admitted_on 是空的")
    return problems


def load(path: Path | None = None) -> list[dict[str, str]]:
    """讀白名單。檔案不存在時回空清單——這樣抓取端會擋掉所有 review 抓取，而不是全部放行。"""
    p = Path(path or WHITELIST)
    if not p.exists():
        return []
    rows: list[dict[str, str]] = []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for i, raw in enumerate(csv.DictReader(fh), start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k}
            row["outlet_key"] = outlet_key(row.get("outlet", ""))
            row["host"] = host_of(row.get("domain", ""))
            row["path_prefix"] = path_prefix_of(row.get("domain", ""))
            row["_line"] = str(i)
            rows.append(row)
    return rows


def check(path: Path | None = None) -> list[str]:
    """回傳違規描述清單（空＝合格）。A21 拿它當判準。"""
    rows = load(path)
    problems: list[str] = []
    if not rows:
        return [f"白名單不存在或是空的：{path or WHITELIST}"]
    for row in rows:
        problems.extend(_bad(row, int(row["_line"])))
    seen: dict[str, str] = {}
    for row in rows:
        key = row["outlet_key"]
        if key in seen:
            problems.append(f"line {row['_line']}: outlet_key {key!r} 與 line {seen[key]} 重複")
        seen[key] = row["_line"]
    return problems


def match(url: str, rows: list[dict[str, str]] | None = None) -> dict[str, str] | None:
    """網址 → 白名單的那一列，比不到回 None。

    主機名必須**完全相同**（只容忍 `www.` 前綴）。子網域不繼承母網域的准入：
    `example.com` 在名單上不會讓 `blog.example.com` 通過（A22）。
    同一個主機下有多列時（例如 `nytimes.com` 與 `nytimes.com/wirecutter`），
    取路徑前綴最長的那一列。
    """
    rows = load() if rows is None else rows
    host = host_of(url)
    path = urlsplit(str(url or "")).path.lower().rstrip("/")
    best: dict[str, str] | None = None
    for row in rows:
        if row["host"] != host or not host:
            continue
        prefix = row["path_prefix"]
        if prefix and not (path == prefix or path.startswith(prefix + "/")):
            continue
        if best is None or len(prefix) > len(best["path_prefix"]):
            best = row
    return best


def admitted(url: str, rows: list[dict[str, str]] | None = None) -> bool:
    return match(url, rows) is not None


def require(url: str, rows: list[dict[str, str]] | None = None) -> dict[str, str]:
    """白名單內就回那一列，否則丟 OutletNotAdmitted。抓取端在送出請求**之前**呼叫它。"""
    row = match(url, rows)
    if row is None:
        raise OutletNotAdmitted(f"不在 outlets.csv 白名單上，不抓：{url}")
    return row
