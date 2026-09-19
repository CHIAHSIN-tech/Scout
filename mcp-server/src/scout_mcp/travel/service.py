"""旅程檔案的讀寫。MCP 工具只是這一層的薄殼。

三條紀律，與既有的 Supabase 那條線一致（instructions.py 第 1 條）：

1. **沒有刪除。** 這裡沒有任何 delete；`upsert_*` 只新增或就地更新，
   不支援「把欄位清空」當作變相刪除。要刪一趟旅程，到檔案總管刪那個資料夾。
2. **所有寫入都經過 `paths.resolve_trip_path()`**，寫不出 `trips/` 之外（A5）。
3. **寫入前一定先驗**。驗不過就整個不寫——半份壞掉的 trip.json 比沒有更糟。

另外：`hours.sources` 是**追加**不是覆蓋。同一家店查到第二個來源時，
兩個都要留著，由建置階段把「來源打架」變成一筆待確認（A13）。
"""

from __future__ import annotations

import json
import secrets
from datetime import date, timedelta
from pathlib import Path

from . import paths
from .schema import (
    DAY_FIELDS,
    EVENT_FIELDS,
    HOURS_IRRELEVANT_KINDS,
    LEG_FIELDS,
    OPEN_QUESTION_FIELDS,
    PLACE_FIELDS,
    dir_name,
    empty_trip,
    validate_trip,
)


class TravelError(ValueError):
    """給 agent 看的錯誤。訊息一律是繁體中文、說得出下一步。"""


# ── 檔案層 ────────────────────────────────────────────────────────────

def _dump(data: dict) -> str:
    """統一的序列化格式。固定 indent、不排序鍵、結尾一個換行——
    build 的決定性（A7）靠的就是這裡沒有任何隨機或時間成分。"""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load(slug: str) -> dict:
    p = paths.trip_json(slug)
    if not p.exists():
        raise TravelError(f"找不到旅程 {slug}。先用 create_trip_file 建立，或用 list_trip_files 看有哪些。")
    return json.loads(p.read_text(encoding="utf-8"))


def save(slug: str, trip: dict) -> Path:
    errs = validate_trip(trip)
    if errs:
        head = "\n".join(f"  - {e}" for e in errs[:10])
        more = f"\n  …還有 {len(errs) - 10} 項" if len(errs) > 10 else ""
        raise TravelError(f"trip.json 結構不合法，沒有寫入任何東西：\n{head}{more}")
    p = paths.trip_json(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_dump(trip), encoding="utf-8", newline="\n")
    return p


# ── 工具背後的實作 ────────────────────────────────────────────────────

def list_trip_files() -> list[dict]:
    """列出所有旅程，依出發日新到舊。壞掉的目錄跳過但會說出來。"""
    root = paths.trips_root()
    out: list[dict] = []
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        f = d / "trip.json"
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta = data.get("trip") or {}
        except (json.JSONDecodeError, OSError) as exc:
            out.append({"slug": d.name, "error": f"讀不出來：{exc}"})
            continue
        out.append({
            "slug": d.name,
            "title": meta.get("title"),
            "country": meta.get("country"),
            "city": meta.get("city"),
            "start_date": meta.get("start_date"),
            "end_date": meta.get("end_date"),
            "page_slug": meta.get("page_slug"),
            "page_path": f"web/trips/{meta.get('page_slug')}/index.html",
            "trip_json": str(f),
        })
    out.sort(key=lambda r: r.get("start_date") or "", reverse=True)
    return out


def create_trip_file(
    *,
    country: str,
    city: str,
    start_date: str,
    end_date: str,
    title: str | None = None,
    party_size: int | None = None,
    currency: str | None = None,
) -> dict:
    """建立骨架。**已存在就回傳既有路徑，絕不覆寫**——重跑一次不該把資料弄丟。"""
    try:
        slug = dir_name(country, city, start_date)
    except ValueError as exc:
        raise TravelError(str(exc)) from exc

    p = paths.trip_json(slug)
    if p.exists():
        return {"slug": slug, "path": str(p), "created": False,
                "note": "這趟已經存在，沒有覆寫。要改內容請用 upsert_* 工具。"}

    # page_slug 的亂碼＝部署路徑的唯一屏障（A15）。只產生一次，之後固定不變，
    # 不然已經發出去的連結會死。
    page_slug = f"{slug}-{secrets.token_hex(3)}"
    trip = empty_trip(
        title=title or f"{city} {start_date}",
        country=country, city=city,
        start_date=start_date, end_date=end_date,
        page_slug=page_slug,
        party_size=party_size, currency=currency,
    )
    saved = save(slug, trip)
    return {"slug": slug, "path": str(saved), "page_slug": page_slug, "created": True}


def _known(table) -> set[str]:
    return {name for name, _, _ in table}


def _clean(payload: dict, table, what: str) -> dict:
    """丟掉 None，擋掉 schema 沒有的欄位。

    未定義的欄位在這裡就擋下來，不等到 validate——這樣錯誤訊息講得出是哪個工具、
    哪個參數打錯，而不是一句「trip.json 有未定義的欄位」。
    """
    allowed = _known(table)
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise TravelError(
            f"{what} 有 schema 沒有的欄位：{unknown}。"
            f"可用的欄位是 {sorted(allowed)}。要新增欄位得先改 travel/schema.py。"
        )
    return {k: v for k, v in payload.items() if v is not None}


def _upsert_into(items: list[dict], item: dict, key: str) -> str:
    """依 key 就地更新或附加。回傳 'updated' / 'added'。"""
    for i, existing in enumerate(items):
        if existing.get(key) == item.get(key):
            merged = dict(existing)
            merged.update(item)
            items[i] = merged
            return "updated"
    items.append(item)
    return "added"


def upsert_place(slug: str, place: dict) -> dict:
    trip = load(slug)
    p = _clean(place, PLACE_FIELDS, "place")
    if not p.get("id"):
        raise TravelError("place 一定要有 id（同一趟裡唯一，例如 'central-reducer'）。")
    places = trip.setdefault("places", [])

    existing = next((x for x in places if x.get("id") == p["id"]), None)
    if existing and "hours" in p:
        # **追加不覆蓋**：第二個來源不該把第一個蓋掉。來源打架是資訊，不是錯誤。
        old = ((existing.get("hours") or {}).get("sources")) or []
        new = (p["hours"] or {}).get("sources") or []
        merged = list(old)
        for s in new:
            if s not in merged:
                merged.append(s)
        p["hours"] = {**(existing.get("hours") or {}), **p["hours"], "sources": merged}

    action = _upsert_into(places, p, "id")
    save(slug, trip)
    return {"slug": slug, "id": p["id"], "action": action, "places": len(places)}


def upsert_event(slug: str, event: dict) -> dict:
    trip = load(slug)
    e = _clean(event, EVENT_FIELDS, "event")
    if not e.get("id"):
        raise TravelError("event 一定要有 id（同一趟裡唯一，例如 'e12'）。")
    events = trip.setdefault("events", [])
    action = _upsert_into(events, e, "id")
    save(slug, trip)
    return {"slug": slug, "id": e["id"], "action": action, "events": len(events)}


def upsert_leg(slug: str, leg: dict) -> dict:
    trip = load(slug)
    g = _clean(leg, LEG_FIELDS, "leg")
    if not g.get("from") or not g.get("to"):
        raise TravelError("leg 一定要有 from 與 to（都得是 places 裡的 id，或 hotel／airport）。")
    legs = trip.setdefault("legs", [])
    # 交通段沒有 id，用 (from, to, day) 當識別。**往返分開存**——
    # 合併成一筆會讓「去 35 分、回 40 分」變成只剩一個數字。
    key = (g["from"], g["to"], g.get("day"))
    action = "added"
    for i, x in enumerate(legs):
        if (x.get("from"), x.get("to"), x.get("day")) == key:
            legs[i] = {**x, **g}
            action = "updated"
            break
    else:
        legs.append(g)
    save(slug, trip)
    return {"slug": slug, "from": g["from"], "to": g["to"], "action": action, "legs": len(legs)}


def upsert_open_question(slug: str, question: dict) -> dict:
    trip = load(slug)
    q = _clean(question, OPEN_QUESTION_FIELDS, "open_question")
    if not q.get("id"):
        raise TravelError("open_question 一定要有 id。")
    qs = trip.setdefault("open_questions", [])
    action = _upsert_into(qs, q, "id")
    save(slug, trip)
    return {"slug": slug, "id": q["id"], "action": action, "open_questions": len(qs)}


def set_trip_section(
    slug: str,
    *,
    sections: dict | None = None,
    stations: list[dict] | None = None,
    days: list[dict] | None = None,
) -> dict:
    """寫入子分頁、車站對照表、每日標題。

    `sections` 是合併（同名的 key 整塊換掉），`stations` 與 `days` 是整份取代——
    它們是表格，逐筆 merge 只會讓「少了一列」變得難以察覺。
    """
    trip = load(slug)
    touched = []
    if sections is not None:
        trip.setdefault("sections", {}).update(sections)
        touched.append(f"sections({','.join(sections)})")
    if stations is not None:
        trip["stations"] = stations
        touched.append(f"stations({len(stations)})")
    if days is not None:
        for d in days:
            _clean(d, DAY_FIELDS, "day")
        trip["days"] = days
        touched.append(f"days({len(days)})")
    if not touched:
        raise TravelError("sections / stations / days 至少要給一個。")
    save(slug, trip)
    return {"slug": slug, "updated": touched}


# ── 自動待確認（A12 / A13）────────────────────────────────────────────

def derive_open_questions(trip: dict) -> list[dict]:
    """從資料本身推出「還沒查證」與「來源打架」兩種待確認。

    決定性：id 由 place id 推出、`check_by` 由出發日往前推三天，
    **不用今天的日期**——用了的話同樣的輸入會建出不一樣的頁面（A7 的位元相同會破）。
    """
    out: list[dict] = []
    meta = trip.get("trip") or {}
    try:
        check_by = (date.fromisoformat(meta["start_date"]) - timedelta(days=3)).isoformat()
    except (KeyError, TypeError, ValueError):
        check_by = None

    used_place_ids = {
        e.get("place_id") for e in (trip.get("events") or []) if isinstance(e, dict)
    }
    locked_place_ids = {
        e.get("place_id") for e in (trip.get("events") or [])
        if isinstance(e, dict) and e.get("locked")
    }
    for p in trip.get("places") or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        sources = ((p.get("hours") or {}).get("sources")) or []
        # 只有真的排進行程的店才問——候補清單上一堆店，全部問會把清單淹掉
        if p["id"] not in used_place_ids:
            continue
        # 開放街區、公園沒有營業時間可查，問了也沒有答案，只會稀釋清單
        if p.get("kind") in HOURS_IRRELEVANT_KINDS:
            continue
        if not sources:
            # 已經訂到位（或事件鎖定）的地方，訂位本身就證明那個時段有開，不必再問「有沒有查證」。
            # 但只省略「未查證」這一種——來源互相矛盾（下面）照樣要問，那是 A13 的硬要求。
            # 特定日期要不要再確認（例如中秋當天）是另一回事，由人寫成手動待確認。
            if p["id"] in locked_place_ids or (p.get("reservation") or {}).get("done"):
                continue
            out.append({
                "id": f"auto-hours-{p['id']}",
                "what": f"「{p.get('name')}」的營業時間還沒查證",
                "why": "行程排了這一站，但頁面上不會印沒查證過的時間",
                "source_hint": "Naver Map／店家官方 IG／Catchtable",
                "auto": True,
                **({"check_by": check_by} if check_by else {}),
            })
            continue
        values = []
        for s in sources:
            v = (s or {}).get("value")
            if v is not None and v not in values:
                values.append(v)
        if len(values) > 1:
            out.append({
                "id": f"auto-hours-conflict-{p['id']}",
                "what": f"「{p.get('name')}」的營業時間有 {len(values)} 個互相矛盾的來源，"
                        "頁面上兩個都會顯示，沒有挑哪一個當正確答案",
                "why": "挑一個等於替使用者決定，而挑錯會讓人撲空",
                "source_hint": "打電話問店家，或以最新一筆 fetched_at 的來源為準",
                "auto": True,
                **({"check_by": check_by} if check_by else {}),
            })
    return out


def merge_auto_questions(trip: dict) -> int:
    """把自動推出的待確認併進 trip。人工寫的同 id 項目不會被蓋掉。"""
    qs = trip.setdefault("open_questions", [])
    existing = {q.get("id") for q in qs if isinstance(q, dict)}
    added = 0
    for q in derive_open_questions(trip):
        if q["id"] in existing:
            continue
        qs.append(q)
        added += 1
    return added


# ── 建置 ──────────────────────────────────────────────────────────────

def build_trip_page(slug: str) -> dict:
    """產出 `trips/<slug>/index.html` 與 `web/trips/<page_slug>/index.html`，更新索引。

    順序有意義：先把自動待確認寫回 trip.json，再渲染——
    頁面上的「出發前待確認」才會跟資料一致，而不是渲染時算一次、存檔時又算一次。
    """
    from .page import render   # 延後 import：schema／service 不該相依渲染器

    trip = load(slug)
    added = merge_auto_questions(trip)
    if added:
        save(slug, trip)

    html = render(trip)

    local = paths.resolve_trip_path(slug, "index.html")
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(html, encoding="utf-8", newline="\n")

    page_slug = (trip.get("trip") or {}).get("page_slug")
    web_dir = paths.web_trips_root() / page_slug
    web_dir.mkdir(parents=True, exist_ok=True)
    (web_dir / "index.html").write_text(html, encoding="utf-8", newline="\n")

    index_path = write_web_index()
    return {
        "slug": slug,
        "local_path": str(local),
        "web_path": str(web_dir / "index.html"),
        "index_path": str(index_path),
        "auto_open_questions_added": added,
    }


def write_web_index() -> Path:
    """重建 `web/trips/index.json`——只列**已經建置過**的旅程。

    只列建置過的，是因為這份索引驅動的是網頁上的連結；列一筆點進去 404 的，
    比少列一筆更糟。
    """
    root = paths.web_trips_root()
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in list_trip_files():
        if r.get("error") or not r.get("page_slug"):
            continue
        if not (root / r["page_slug"] / "index.html").exists():
            continue
        rows.append({
            # slug 是資料夾名稱，上傳頁的下拉選單要用它當 value
            # （page_path 裡的是 page_slug，帶亂碼，不是附件的歸屬 key）
            "slug": r["slug"],
            "country": r["country"],
            "city": r["city"],
            "start_date": r["start_date"],
            "end_date": r["end_date"],
            "title": r["title"],
            "page_path": f"trips/{r['page_slug']}/index.html",
        })
    rows.sort(key=lambda r: r.get("start_date") or "", reverse=True)
    p = root / "index.json"
    p.write_text(_dump(rows), encoding="utf-8", newline="\n")
    return p
