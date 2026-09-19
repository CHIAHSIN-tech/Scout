"""把 trip.json 轉成 .ics 與地圖 CSV。

為什麼在建置時就產好、而不是在頁面上用 JS 現算：
產出要是決定性的（A7），而且離線單檔裡多一份算式就多一個會壞的地方。
建置時算完、把結果內嵌，頁面上只剩「把字串存成檔案」這一個動作。

欄位與格式刻意跟 `web/export-formats.js` 對齊——同一個 Scout 匯出的東西，
不該因為走哪一條線而長得不一樣。
"""

from __future__ import annotations

from ..schema import day_date

DEFAULT_DUR_MIN = 60           # 沒填停留時間時的預設，與 export-formats.js 同值
CSV_HEADER = ("name", "location", "day", "time", "notes")


def _esc(s) -> str:
    r""".ics 的跳脫：反斜線、分號、逗號前面加反斜線，換行寫成 \n。"""
    out = str(s if s is not None else "")
    out = out.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return out.replace("\r\n", "\\n").replace("\n", "\\n")


def _stamp(the_date, minutes: int) -> str:
    """日期 ＋ 一天中的第幾分鐘 → `YYYYMMDDTHHMMSS`（浮動時間，不帶時區）。

    刻意用浮動時間：出國時「晚餐 19:00」指的是當地的 19:00，
    帶時區反而會在回台灣之後把整趟行程平移一小時。
    """
    iso = the_date.isoformat() if hasattr(the_date, "isoformat") else str(the_date)
    d = iso.replace("-", "")
    minutes %= 24 * 60
    return f"{d}T{minutes // 60:02d}{minutes % 60:02d}00"


def _minutes(hhmm) -> int | None:
    try:
        h, m = str(hhmm).split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _places(trip):
    return {p["id"]: p for p in (trip.get("places") or []) if isinstance(p, dict) and p.get("id")}


def _where(trip, ev, places):
    """事件的地點字串。找不到店就退回旅館／機場這種保留 id 的名字。"""
    pid = ev.get("place_id")
    p = places.get(pid)
    if p:
        addr = (p.get("location") or {}).get("address")
        name = p.get("name") or pid
        return f"{name}（{addr}）" if addr and addr != "unknown" else name
    if pid == "hotel":
        beds = trip.get("lodging") or []
        return (beds[0].get("name") or "旅館") if beds else "旅館"
    return {"airport": "機場", "station": "車站", "home": "家"}.get(pid, "")


def build_ics(trip: dict) -> str:
    """整趟行程 → 一份 .ics。匯進手機日曆之後，出門不用開任何 app 也會跳提醒。"""
    meta = trip.get("trip") or {}
    start = meta.get("start_date") or ""
    slug = meta.get("page_slug") or "trip"
    # DTSTAMP 不能用「現在」——那會讓同一份資料每次建置都不一樣（A7）。
    # 用出發日當戳記：它是資料的一部分，不是環境的一部分。
    dtstamp = f"{start.replace('-', '')}T000000Z" if start else "20000101T000000Z"
    places = _places(trip)

    evs = [e for e in (trip.get("events") or [])
           if isinstance(e, dict) and e.get("day") and e.get("time")]
    evs.sort(key=lambda e: (e["day"], e["time"], e.get("id") or ""))

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Scout//Trip Page//ZH-TW",
             "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_esc(meta.get('title') or '行程')}"]
    for i, ev in enumerate(evs):
        begin = _minutes(ev["time"])
        date = day_date(trip, ev["day"])
        if begin is None or date is None:
            continue
        # 停留時間：有寫就用寫的；沒寫就看同一天下一項幾點開始，兩者都沒有才用預設值
        dur = ev.get("dur_min")
        if not dur:
            nxt = next((n for n in evs[i + 1:] if n["day"] == ev["day"]), None)
            gap = (_minutes(nxt["time"]) - begin) if nxt and _minutes(nxt["time"]) is not None else None
            dur = gap if gap and 0 < gap <= 8 * 60 else DEFAULT_DUR_MIN
        lines += ["BEGIN:VEVENT",
                  f"UID:scout-{slug}-{ev.get('id') or i}@scout.local",
                  f"DTSTAMP:{dtstamp}",
                  f"DTSTART:{_stamp(date, begin)}",
                  f"DTEND:{_stamp(date, begin + int(dur))}",
                  f"SUMMARY:{_esc(ev.get('title') or '行程')}"]
        where = _where(trip, ev, places)
        if where:
            lines.append(f"LOCATION:{_esc(where)}")
        if ev.get("note"):
            lines.append(f"DESCRIPTION:{_esc(ev['note'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _csv_cell(v) -> str:
    """RFC4180：含逗號／引號／換行就整格加引號，內部引號重複一次。"""
    s = str(v if v is not None else "")
    return '"' + s.replace('"', '""') + '"' if any(c in s for c in ',"\r\n') else s


def build_map_csv(trip: dict) -> str:
    """有地址的地點 → Google My Maps 吃得下的 CSV。沒有地點的事件不輸出。"""
    rows = [",".join(CSV_HEADER)]
    places = _places(trip)
    evs = sorted((e for e in (trip.get("events") or []) if isinstance(e, dict)),
                 key=lambda e: (e.get("day") or 99, e.get("time") or "", e.get("id") or ""))
    for ev in evs:
        p = places.get(ev.get("place_id"))
        if not p:
            continue
        addr = (p.get("location") or {}).get("address")
        # 沒有地址就退回當地名稱：Google My Maps 用店名也查得到，空字串則完全沒用
        where = addr if addr and addr != "unknown" else (p.get("name_local") or p.get("name") or "")
        if not where:
            continue
        rows.append(",".join(_csv_cell(x) for x in (
            p.get("name") or ev.get("title") or "", where,
            ev.get("day") or "", ev.get("time") or "", ev.get("note") or "")))
    return "\r\n".join(rows) + "\r\n"
