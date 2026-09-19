"""得獎名單：涵蓋沒有電商、也不會出現在 FDC 的小廠。

Scovie Awards、World Hot Sauce Awards、NYC Hot Sauce Expo 每年逐項列出得獎者，
那是一份別的地方拿不到的母體切片——一年做兩百瓶的廠不會有 GTIN，
但它會去比賽，而且會得獎。

**要掃哪些頁寫在 `fixtures/sauce/awards.csv`，不寫在程式裡。** 這些站每年改版、
網址每年變，把它們寫死在程式裡等於每年都要改程式；寫成 fixture 則是改一列 CSV，
而且那一列本身就是「這一屆我們看的是這一頁」的紀錄。
"""
from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from typing import Any

from evdb.schema import Event, Precision

from .. import harvest
from ..net import Fetcher
from ..outlets import FIXTURES
from . import filters

SOURCE = "awards"
AWARDS_CSV = FIXTURES / "awards.csv"
COLUMNS = ("award", "year", "url", "format", "note")

#: 名次標記。Scovie 的得獎名錄就是用這幾個字把一筆一筆隔開的。
PLACEMENTS = ("1st", "2nd", "3rd", "hm", "honorable mention")

#: 得獎名錄裡有承辦人姓名、email、電話、通訊地址。**那些一概不取。**
#: 我們要的是「有這款產品、是哪家公司做的」，不是一份可以拿來寄信的名單；
#: 把個人資料一起收進語料庫，事後從任何一張表上都看不出來，但它就在庫裡了。
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_ADDRESS = re.compile(r"\d+\s+\w+|P\s?O\s?Box|\b[A-Z]{2}\s+\d{5}\b", re.I)
_URLISH = re.compile(r"(?:https?://|www\.)|\.(?:com|net|org|co|us|shop)\b", re.I)


def _is_personal(line: str) -> bool:
    return bool(_EMAIL.search(line) or _PHONE.search(line) or _ADDRESS.search(line))

_ROW = re.compile(rb"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(rb"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
_ITEM = re.compile(rb"<li\b[^>]*>(.*?)</li>", re.I | re.S)
_TAGS = re.compile(rb"<[^>]+>")


def _text(raw: bytes) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(b" ", raw).decode("utf-8", "replace"))).strip()


def load_config(path: Path | None = None) -> list[dict[str, str]]:
    p = Path(path or AWARDS_CSV)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k}
                for r in csv.DictReader(fh)]


def to_events(cfg: dict[str, str], page: bytes, observed_at: str) -> list[Event]:
    """表格列與清單項都掃；名字過不了辣醬規則的就不收（得獎名單裡也有辣椒粉與莎莎醬）。"""
    seen: set[str] = set()
    out: list[Event] = []
    chunks = [(_text(m.group(1)), _text(m.group(1)))
              for m in _ITEM.finditer(page)]
    for row in _ROW.finditer(page):
        cells = [_text(c) for c in _CELL.findall(row.group(1))]
        if cells:
            chunks.append((cells[0], " | ".join(cells[:4])))
    year = cfg.get("year", "")
    for name, note in chunks:
        name = name.strip(" -–—•*")
        if not (3 <= len(name) <= 120) or name.lower() in seen:
            continue
        if not filters.keep(name, "", note):
            continue
        seen.add(name.lower())
        key = f"{cfg.get('award', 'award')}-{year}-{len(seen)}"
        out.append(harvest.mention_event(
            source=SOURCE, key=key, name=name, url=cfg.get("url"),
            observed_at=observed_at,
            event_time=year if year[:4].isdigit() else None,
            precision=Precision.YEAR.value,
            payload={"award": cfg.get("award", ""), "year": year, "row": note[:400],
                     "note": cfg.get("note", "")}))
    return out


def pdf_text(blob: bytes) -> str:
    """得獎名錄多半是 PDF。文字型 PDF 直接取文字；掃描型取不到就回空字串，不猜。"""
    try:
        import io

        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(io.BytesIO(blob))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def parse_directory(text: str, cfg: dict[str, str]) -> list[dict[str, str]]:
    """名錄的版面：`分類 -> 子分類` / `1st` / 產品名 / 公司名 / 承辦人與聯絡方式。

    只取分類、名次、產品名、公司名、公司網址。承辦人姓名與所有聯絡方式一律丟掉
    （見 `_is_personal` 的說明）。
    """
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    out: list[dict[str, str]] = []
    category = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if "->" in line and len(line) < 200:
            category = line
            i += 1
            continue
        if line.lower().strip(".:") in PLACEMENTS:
            placement = line.strip(".:")
            fields: list[str] = []
            j = i + 1
            while j < len(lines) and len(fields) < 2:
                nxt = lines[j]
                j += 1
                if not nxt:
                    continue
                if nxt.lower().strip(".:") in PLACEMENTS or "->" in nxt:
                    break
                if _is_personal(nxt) or _URLISH.search(nxt):
                    continue
                fields.append(nxt)
            if fields:
                out.append({"placement": placement, "category": category,
                            "product": fields[0],
                            "company": fields[1] if len(fields) > 1 else "",
                            "award": cfg.get("award", ""), "year": cfg.get("year", "")})
            i = j
            continue
        i += 1
    return out


#: 名錄的分類欄本身就是評審的分類。分類寫著 Hot Sauce 的那一格，裡面每一筆都是辣醬，
#: 名字叫「Pineapple Xpress」也一樣——再套一次名稱規則等於把小廠的品名全部丟掉
#: （實測：套了之後 1,000 筆只留下 86 筆）。
#: 比對的是 `->` **左邊**那一段（評審的「組別」），不是整串。
#: `Condiments-Hot & Spicy ->Ketchup` 的組別是調味料，不是辣醬——番茄醬再辣也是番茄醬。
AUTHORITATIVE_CATEGORY = re.compile(
    r"^\s*(hot sauce|chile sauce|chili sauce|pepper sauce|salsa)", re.I)

#: 先看否定。`Barbecue Dry Rubs and Seasonings-Not Hot & Spicy` 含有 "hot & spicy"
#: 這四個字，但它的意思正好相反——只做正向比對會把整區乾燥調味料收進辣醬母體。
CATEGORY_VETO = re.compile(
    r"not hot|dry rub|seasoning|jerky|snack|nut|candy|chocolate|dessert|"
    r"advertising|marketing|label|packaging|logo|website|display", re.I)

#: 名錄的欄位順序是 產品／公司／承辦人。公司欄空著的時候，下一行就是**人名**。
#: 這些是自然人的姓名，不該進語料庫，所以看起來像人名（兩個字、沒有任何公司字樣）
#: 的就當作沒有品牌——寧可少一個品牌，不要多一個人的名字。
_CORPORATE = re.compile(
    r"\b(llc|l\.l\.c|inc|co|corp|company|companies|foods?|farms?|kitchen|brands?|"
    r"sauce|sauces|spice|spices|pepper|peppers|trading|provisions|works|labs?|"
    r"gourmet|market|mills?|bros|brothers|&|'s)\b", re.I)


def _looks_like_person(name: str) -> bool:
    words = name.split()
    return (2 <= len(words) <= 3 and not _CORPORATE.search(name)
            and all(w[:1].isupper() for w in words if w))

#: 這份 PDF 的字型把 tt／ti 之類的連字丟成 `[`（`h[ps://` 其實是 `https://`）。
#: 那是文件本身的問題，兩種抽取器都一樣。**不猜、不自動修**——修錯了事後看不出來。
#: 受影響的列照收，但標記起來，讓比對層與報告知道這個名字不是逐字可信的。
_LIGATURE_LOSS = re.compile(r"\w\[\w")


_DOMAIN = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9-]{2,62}\.(?:com|net|org|co|us|shop|store))",
                     re.I)
#: 名錄裡也會出現這些，它們不是廠商自己的店
_NOT_A_STORE = ("scovieawards", "fieryfoodscentral", "jotform", "facebook", "instagram",
                "square.site", "etsy", "amazon", "gmail", "yahoo", "hotmail", "outlook",
                "wixsite", "godaddysites", "shopify.com", "bigcartel")


def company_domains(text: str) -> list[str]:
    """得獎名錄裡的**公司網址**。這是長尾店面名單最好的來源。

    一年一千筆得獎紀錄，每一筆都附著廠商自己的網站——那是一份別的地方拿不到的
    小廠名冊。從這裡撈網域、再逐一確認它是不是一間賣辣醬的店，比用品牌名去猜網域準得多。

    只取公司網址；承辦人的 email、電話、地址一概不取（見 `_is_personal`）。
    社群平台、表單服務、市集頁不算店面。
    """
    seen: dict[str, None] = {}
    for line in text.splitlines():
        if _EMAIL.search(line):
            continue                      # email 裡也有網域，但那是個人聯絡方式
        for m in _DOMAIN.finditer(line):
            domain = m.group(1).lower()
            if any(bad in domain for bad in _NOT_A_STORE):
                continue
            seen.setdefault(domain, None)
    return list(seen)


def directory_events(cfg: dict[str, str], rows: list[dict[str, str]],
                     observed_at: str) -> list[Event]:
    out: list[Event] = []
    year = cfg.get("year", "")
    for n, row in enumerate(rows, start=1):
        name = row["product"]
        if not (3 <= len(name) <= 120):
            continue
        category = row["category"]
        division = category.split("->")[0]
        authoritative = bool(AUTHORITATIVE_CATEGORY.search(division)
                             and not CATEGORY_VETO.search(category))
        if CATEGORY_VETO.search(category):
            continue
        if not authoritative and not filters.keep(name, "", row["category"]):
            continue
        out.append(harvest.mention_event(
            source=SOURCE, key=f"{cfg.get('award', 'award')}-{year}-{n}",
            name=name, brand="" if _looks_like_person(row["company"]) else row["company"],
            url=cfg.get("url"),
            observed_at=observed_at,
            event_time=year if year[:4].isdigit() else None,
            precision=Precision.YEAR.value,
            payload={"award": row["award"], "year": year, "category": row["category"],
                     "placement": row["placement"], "note": cfg.get("note", ""),
                     "category_is_authoritative": authoritative,
                     "text_fidelity": ("ligature_loss"
                                       if _LIGATURE_LOSS.search(name + " " + row["company"])
                                       else "verbatim")}))
    return out


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                config: Path | None = None, log: Any = None) -> dict[str, Any]:
    rows = load_config(config)
    events: list[Event] = []
    pages = []
    for cfg in rows:
        got = fetcher.get(cfg["url"])
        if not got.ok:
            pages.append({"url": cfg["url"], "reason": got.reason, "kept": 0})
            if log:
                print(f"  awards {cfg['award']:<28} SKIP {got.reason}", file=log, flush=True)
            continue
        is_pdf = (cfg.get("format") == "directory_pdf"
                  or cfg["url"].lower().endswith(".pdf"))
        snapshot.write(SOURCE,
                       f"{cfg.get('award', 'a')}-{cfg.get('year', '')}."
                       f"{'pdf' if is_pdf else 'html'}".replace("/", "_"), got.body)
        if is_pdf:
            text = pdf_text(got.body)
            found = directory_events(cfg, parse_directory(text, cfg), observed_at)
        else:
            found = to_events(cfg, got.body, observed_at)
        events.extend(found)
        pages.append({"url": cfg["url"], "reason": "", "kept": len(found)})
        if log:
            print(f"  awards {cfg['award']:<28} {cfg.get('year', ''):<6} kept={len(found)}",
                  file=log, flush=True)
    return {"source": SOURCE, "pages": pages, "events": events, "kept": len(events),
            "reason": "" if rows else "no_config"}
