"""trip.json 的欄位定義與不變式——**本模組是唯一一份欄位清單**。

任何地方要驗 trip.json 的結構都 import 這裡（規格 EXECUTION RULES 5：
「共用型別只有一份……不得出現第二份欄位清單」）。渲染器、服務層、
命令列驗證器、測試，全部從這裡取欄位。

刻意不用 pydantic：這份 schema 的價值在於「一眼看得出有哪些欄位、哪些是必填」，
宣告式的表格比一堆 model class 更容易被人逐條核對。驗證器回傳的是
**繁體中文的錯誤字串清單**，因為它的讀者是 agent 與使用者，不是 traceback。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

SCHEMA_VERSION = 1

# render() 的簽章由 N1 凍結，N2 只能照這個呼叫、N3 只能照這個實作。
RENDER_SIGNATURE = "scout_mcp.travel.page.render(trip: dict) -> str"

# 目錄命名規則：<YYYY>-<MM>-<ISO3166-1 alpha-2 小寫>-<城市 slug>
DIR_NAME_RE = re.compile(r"^\d{4}-\d{2}-[a-z]{2}-[a-z0-9-]+$")
# 部署路徑再加 6 碼以上的十六進位亂碼（A15：路徑不可猜）
PAGE_SLUG_RE = re.compile(r"^\d{4}-\d{2}-[a-z]{2}-[a-z0-9-]+-[0-9a-f]{6,}$")

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# events[].place_id 與 legs[].from/to 允許這些「不是店家」的保留 id。
RESERVED_PLACE_IDS = frozenset({"hotel", "airport", "station", "home"})

EVENT_TYPES = frozenset({"shopping", "meal", "move", "sight", "service"})
PLACE_KINDS = frozenset({"meal", "shopping", "sight", "service", "cafe", "queue"})
LEG_MODES = frozenset({"subway", "bus", "taxi", "walk", "train", "air", "other"})

# ── 欄位表 ────────────────────────────────────────────────────────────
# 每個項目是 (欄位名, 型別 tuple, 是否必填)。None 值一律視為「沒給」。
# 這張表就是規格資料模型的可執行版本。

_STR = (str,)
_NUM = (int, float)
_BOOL = (bool,)
_LIST = (list,)
_DICT = (dict,)

TOP_LEVEL_FIELDS = [
    ("schema_version", (int,), True),
    ("trip", _DICT, True),
    ("flights", _LIST, False),
    ("lodging", _LIST, False),
    ("places", _LIST, False),
    ("events", _LIST, False),
    ("legs", _LIST, False),
    ("open_questions", _LIST, False),
    ("stations", _LIST, False),
    ("sections", _DICT, False),
    ("map", _DICT, False),
]

TRIP_FIELDS = [
    ("title", _STR, True),
    ("country", _STR, True),
    ("country_name", _STR, False),
    ("city", _STR, True),
    ("city_name", _STR, False),
    ("start_date", _STR, True),
    ("end_date", _STR, True),
    ("party_size", (int,), False),
    ("currency", _STR, False),
    ("budget", _DICT, False),
    ("notes", _STR, False),
    ("supabase_trip_id", (int,), False),
    ("page_slug", _STR, True),
]

FLIGHT_FIELDS = [
    ("dir", _STR, True),          # out / back
    ("date", _STR, True),
    ("from", _STR, True),
    ("to", _STR, True),
    ("dep", _STR, False),
    ("arr", _STR, False),
    ("arr_next_day", _BOOL, False),
    ("no", _STR, False),
    ("terminal", _STR, False),
    ("note", _STR, False),
    ("locked", _BOOL, False),
]

LODGING_FIELDS = [
    ("name", _STR, True),
    ("station", _STR, False),
    ("check_in", _STR, False),
    ("check_out", _STR, False),
    ("address", _STR, False),
    ("lat", _NUM, False),
    ("lon", _NUM, False),
    ("booking_ref", _STR, False),
    ("notes", _STR, False),
    ("locked", _BOOL, False),
]

PLACE_FIELDS = [
    ("id", _STR, True),
    ("name", _STR, True),
    ("name_local", _STR, False),
    ("name_zh", _STR, False),
    ("kind", _STR, False),
    ("cuisine", _LIST, False),
    ("area", _STR, False),
    ("district", _STR, False),
    ("price_band", _DICT, False),
    ("hours", _DICT, False),
    ("reservation", _DICT, False),
    ("location", _DICT, False),
    ("queue_only", _BOOL, False),
    ("alert", _STR, False),
    ("sources", _LIST, False),
    ("notes", _STR, False),
    ("extra", _DICT, False),
]

EVENT_FIELDS = [
    ("id", _STR, True),
    ("day", (int,), True),
    ("time", _STR, True),
    ("dur_min", (int,), False),
    ("min_dur_min", (int,), False),
    ("type", _STR, False),
    ("title", _STR, True),
    ("place_id", _STR, False),
    ("locked", _BOOL, False),
    ("sunset_locked", _BOOL, False),
    ("links", _LIST, False),
    ("note", _STR, False),
]

LEG_FIELDS = [
    ("from", _STR, True),
    ("to", _STR, True),
    ("day", (int,), False),
    ("mode", _STR, False),
    ("lines", _LIST, False),
    ("transfer_at", _LIST, False),
    ("min", (int,), False),
    ("label", _STR, False),
    ("label_t", _NUM, False),
    ("label_dx", _NUM, False),
    ("label_dy", _NUM, False),
]

OPEN_QUESTION_FIELDS = [
    ("id", _STR, True),
    ("date", _STR, False),
    ("what", _STR, True),
    ("why", _STR, False),
    ("check_by", _STR, False),
    ("source_hint", _STR, False),
    ("auto", _BOOL, False),
]

STATION_FIELDS = [
    ("en", _STR, True),
    ("zh", _STR, False),
    ("local", _STR, False),
    ("lines", _LIST, False),
    ("days", _LIST, False),
]

MAP_FIELDS = [
    ("lon0", _NUM, False),
    ("lon1", _NUM, False),
    ("lat0", _NUM, False),
    ("lat1", _NUM, False),
    ("river", _LIST, False),
]

# 供渲染器與匯入器查「某個物件允許哪些欄位」，不用各自再寫一份。
FIELD_TABLES = {
    "trip": TRIP_FIELDS,
    "flight": FLIGHT_FIELDS,
    "lodging": LODGING_FIELDS,
    "place": PLACE_FIELDS,
    "event": EVENT_FIELDS,
    "leg": LEG_FIELDS,
    "open_question": OPEN_QUESTION_FIELDS,
    "station": STATION_FIELDS,
    "map": MAP_FIELDS,
}


# ── 小工具 ────────────────────────────────────────────────────────────

def slugify_city(city: str) -> str:
    """城市名 → 目錄用 slug。

    只留小寫英數與連字號。**刻意不處理非拉丁文字的音譯**——
    轉不出來就回空字串，由呼叫端報錯，不猜。
    """
    norm = unicodedata.normalize("NFKD", city or "")
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")


def dir_name(country: str, city: str, start_date: str) -> str:
    """組出 `<YYYY>-<MM>-<cc>-<city>`。格式不合法時丟 ValueError。"""
    if not DATE_RE.match(start_date or ""):
        raise ValueError(f"start_date 必須是 YYYY-MM-DD，收到 {start_date!r}")
    cc = (country or "").strip().lower()
    if not re.fullmatch(r"[a-z]{2}", cc):
        raise ValueError(f"country 必須是 ISO 3166-1 alpha-2 兩碼，收到 {country!r}")
    slug = slugify_city(city)
    if not slug:
        raise ValueError(f"city 轉不出 slug（需要拉丁字母），收到 {city!r}")
    return f"{start_date[:7]}-{cc}-{slug}"


def day_count(trip: dict) -> int:
    """旅程總天數（含頭尾）。日期不合法時回 0。"""
    meta = (trip or {}).get("trip") or {}
    try:
        s = date.fromisoformat(meta["start_date"])
        e = date.fromisoformat(meta["end_date"])
    except (KeyError, TypeError, ValueError):
        return 0
    return (e - s).days + 1 if e >= s else 0


def day_date(trip: dict, day: int) -> date | None:
    """第 n 天是哪一天。超出範圍回 None。"""
    meta = (trip or {}).get("trip") or {}
    try:
        s = date.fromisoformat(meta["start_date"])
    except (KeyError, TypeError, ValueError):
        return None
    if day < 1 or day > day_count(trip):
        return None
    return s + timedelta(days=day - 1)


# ── 驗證 ──────────────────────────────────────────────────────────────

def _check_fields(obj, table, label, errs):
    if not isinstance(obj, dict):
        errs.append(f"{label} 必須是物件，收到 {type(obj).__name__}")
        return
    allowed = {name for name, _, _ in table}
    for name, types, required in table:
        if name not in obj or obj[name] is None:
            if required:
                errs.append(f"{label} 缺少必填欄位 {name}")
            continue
        value = obj[name]
        # bool 是 int 的子類別，數值欄位不該吃 True
        if int in types and isinstance(value, bool) and bool not in types:
            errs.append(f"{label}.{name} 型別錯誤：期望數字，收到 bool")
            continue
        if not isinstance(value, types):
            want = "/".join(t.__name__ for t in types)
            errs.append(f"{label}.{name} 型別錯誤：期望 {want}，收到 {type(value).__name__}")
    for key in obj:
        if key not in allowed:
            errs.append(f"{label} 有未定義的欄位 {key}（新欄位要先加進 schema.py）")


def validate_place(place: dict, label: str = "place") -> list[str]:
    """單一 place 的結構檢查。`extra{}` 裡面不檢查——那是刻意的收納箱。"""
    errs: list[str] = []
    _check_fields(place, PLACE_FIELDS, label, errs)
    if not isinstance(place, dict):
        return errs
    kind = place.get("kind")
    if kind is not None and kind not in PLACE_KINDS:
        errs.append(f"{label}.kind 必須是 {sorted(PLACE_KINDS)} 之一，收到 {kind!r}")
    hours = place.get("hours")
    if isinstance(hours, dict):
        sources = hours.get("sources")
        if sources is None:
            errs.append(f"{label}.hours 必須有 sources 陣列（空陣列＝未查證，不是省略）")
        elif not isinstance(sources, list):
            errs.append(f"{label}.hours.sources 必須是陣列")
        else:
            for i, s in enumerate(sources):
                if not isinstance(s, dict) or "value" not in s:
                    errs.append(f"{label}.hours.sources[{i}] 需要至少有 value 欄位")
    return errs


def validate_places(places) -> list[str]:
    """一批 places（給 import_reference 的輸出用）。"""
    if not isinstance(places, list):
        return ["places 必須是陣列"]
    errs: list[str] = []
    seen: set[str] = set()
    for i, p in enumerate(places):
        errs.extend(validate_place(p, f"places[{i}]"))
        pid = p.get("id") if isinstance(p, dict) else None
        if isinstance(pid, str):
            if pid in seen:
                errs.append(f"places[{i}].id 重複：{pid}")
            seen.add(pid)
    return errs


def validate_trip(trip) -> list[str]:
    """整份 trip.json。回傳錯誤字串清單，空清單＝通過。"""
    if not isinstance(trip, dict):
        return ["trip.json 的最外層必須是物件"]

    errs: list[str] = []
    _check_fields(trip, TOP_LEVEL_FIELDS, "trip.json", errs)
    if trip.get("schema_version") not in (None, SCHEMA_VERSION):
        errs.append(
            f"schema_version 只支援 {SCHEMA_VERSION}，收到 {trip.get('schema_version')!r}"
        )

    meta = trip.get("trip")
    if isinstance(meta, dict):
        _check_fields(meta, TRIP_FIELDS, "trip", errs)
        for f in ("start_date", "end_date"):
            v = meta.get(f)
            if isinstance(v, str) and not DATE_RE.match(v):
                errs.append(f"trip.{f} 必須是 YYYY-MM-DD，收到 {v!r}")
        slug = meta.get("page_slug")
        if isinstance(slug, str) and not PAGE_SLUG_RE.match(slug):
            errs.append(
                f"trip.page_slug 不符合 <YYYY>-<MM>-<cc>-<city>-<6 碼以上亂碼>：{slug!r}"
            )

    n_days = day_count(trip)
    if n_days <= 0:
        errs.append("無法由 start_date / end_date 算出天數（end_date 不得早於 start_date）")

    for i, f in enumerate(trip.get("flights") or []):
        _check_fields(f, FLIGHT_FIELDS, f"flights[{i}]", errs)
        if isinstance(f, dict) and f.get("dir") not in (None, "out", "back"):
            errs.append(f"flights[{i}].dir 只能是 out 或 back")
    for i, l in enumerate(trip.get("lodging") or []):
        _check_fields(l, LODGING_FIELDS, f"lodging[{i}]", errs)

    place_ids: set[str] = set()
    for i, p in enumerate(trip.get("places") or []):
        errs.extend(validate_place(p, f"places[{i}]"))
        pid = p.get("id") if isinstance(p, dict) else None
        if isinstance(pid, str):
            if pid in place_ids:
                errs.append(f"places[{i}].id 重複：{pid}")
            if pid in RESERVED_PLACE_IDS:
                errs.append(f"places[{i}].id 不能用保留字 {pid}")
            place_ids.add(pid)
    known = place_ids | RESERVED_PLACE_IDS

    event_ids: set[str] = set()
    for i, e in enumerate(trip.get("events") or []):
        _check_fields(e, EVENT_FIELDS, f"events[{i}]", errs)
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        if isinstance(eid, str):
            if eid in event_ids:
                errs.append(f"events[{i}].id 重複：{eid}")
            event_ids.add(eid)
        day = e.get("day")
        if isinstance(day, int) and not isinstance(day, bool):
            if n_days > 0 and not 1 <= day <= n_days:
                errs.append(f"events[{i}].day={day} 超出 1..{n_days}")
        t = e.get("time")
        if isinstance(t, str) and not TIME_RE.match(t):
            errs.append(
                f"events[{i}].time 必須是 HH:MM（目的地當地時間，不換算時區），收到 {t!r}"
            )
        typ = e.get("type")
        if typ is not None and typ not in EVENT_TYPES:
            errs.append(f"events[{i}].type 必須是 {sorted(EVENT_TYPES)} 之一，收到 {typ!r}")
        ref = e.get("place_id")
        if isinstance(ref, str) and ref not in known:
            errs.append(f"events[{i}].place_id={ref!r} 不存在於 places（也不是保留 id）")

    for i, g in enumerate(trip.get("legs") or []):
        _check_fields(g, LEG_FIELDS, f"legs[{i}]", errs)
        if not isinstance(g, dict):
            continue
        for side in ("from", "to"):
            ref = g.get(side)
            if isinstance(ref, str) and ref not in known:
                errs.append(f"legs[{i}].{side}={ref!r} 不存在於 places（也不是保留 id）")
        mode = g.get("mode")
        if mode is not None and mode not in LEG_MODES:
            errs.append(f"legs[{i}].mode 必須是 {sorted(LEG_MODES)} 之一，收到 {mode!r}")
        day = g.get("day")
        if isinstance(day, int) and not isinstance(day, bool) and n_days > 0:
            if not 1 <= day <= n_days:
                errs.append(f"legs[{i}].day={day} 超出 1..{n_days}")

    q_ids: set[str] = set()
    for i, q in enumerate(trip.get("open_questions") or []):
        _check_fields(q, OPEN_QUESTION_FIELDS, f"open_questions[{i}]", errs)
        if isinstance(q, dict) and isinstance(q.get("id"), str):
            if q["id"] in q_ids:
                errs.append(f"open_questions[{i}].id 重複：{q['id']}")
            q_ids.add(q["id"])

    for i, s in enumerate(trip.get("stations") or []):
        _check_fields(s, STATION_FIELDS, f"stations[{i}]", errs)

    if isinstance(trip.get("map"), dict) and trip["map"]:
        _check_fields(trip["map"], MAP_FIELDS, "map", errs)

    return errs


def empty_trip(
    *,
    title: str,
    country: str,
    city: str,
    start_date: str,
    end_date: str,
    page_slug: str,
    party_size: int | None = None,
    currency: str | None = None,
) -> dict:
    """建檔用的骨架。只放必填欄位，其餘留給 upsert_* 一個個補。"""
    meta = {
        "title": title,
        "country": country.strip().lower(),
        "city": city,
        "start_date": start_date,
        "end_date": end_date,
        "page_slug": page_slug,
    }
    if party_size is not None:
        meta["party_size"] = party_size
    if currency is not None:
        meta["currency"] = currency
    return {
        "schema_version": SCHEMA_VERSION,
        "trip": meta,
        "flights": [],
        "lodging": [],
        "places": [],
        "events": [],
        "legs": [],
        "open_questions": [],
        "stations": [],
        "sections": {},
        "map": {},
    }
