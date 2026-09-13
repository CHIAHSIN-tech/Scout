"""排程衝突檢查——**只回報，永遠不修改任何東西**（規格 A11）。

這是本模組最重要的一條紀律，所以寫在最上面：
這支程式不會刪行程、不會搬行程、不會「幫你調整一下」。它只回答兩件事——
**哪裡撞到了**、**要解掉它得犧牲什麼**。取捨由人決定。

理由來自參考產品第 3.1 節第 5 步：塞不下的時候，程式自己挑一個砍掉，
使用者不會知道自己失去了什麼；把選項攤開來，他才選得下去。

檢查五類衝突：
    locked          鎖定項目被要求移動
    hours           候選點的營業時間不覆蓋該時段（或當天公休）
    dwell           交通時間吃掉指定停留時長（可用時間 < min_dur_min）
    night           21:00 後跨區移動，且最後一站不在旅館步行範圍
    sunset          sunset_locked 項目抵達晚於日落前 60 分

查不到資料時**不當成通過，也不當成衝突**——回一筆 `unverified`，
那是 `open_questions` 的原料，不是「沒問題」。
"""

from __future__ import annotations

import re

from .schema import HOURS_IRRELEVANT_KINDS, TIME_RE, day_count, day_date, find_leg

# 日落前多久必須抵達（分鐘）。參考產品的規則。
SUNSET_LEAD_MIN = 60
# 幾點以後的移動算「夜間動線」
NIGHT_HOUR = 21

_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
# 營業時間是自由文字（中韓混雜），只抽得出 HH:MM–HH:MM 這種區間。
# 抽不出來就是「查不到」，不是「全天營業」。
_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[-–~〜到至]\s*(\d{1,2}):(\d{2})")


def to_min(hhmm: str) -> int | None:
    if not isinstance(hhmm, str) or not TIME_RE.match(hhmm):
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _fmt(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _places(trip: dict) -> dict[str, dict]:
    return {p["id"]: p for p in (trip.get("places") or []) if isinstance(p, dict) and p.get("id")}


def _days(trip: dict) -> dict[int, dict]:
    return {d["day"]: d for d in (trip.get("days") or []) if isinstance(d, dict) and "day" in d}



def _hours_ranges(place: dict) -> tuple[list[tuple[int, int]] | None, list[str]]:
    """回傳 (可營業區間, 公休日)。抽不出區間時回 (None, ...)＝查不到，不是全天開。"""
    hours = place.get("hours") or {}
    sources = hours.get("sources") or []
    if not sources:
        return None, []
    ranges: list[tuple[int, int]] = []
    closed: list[str] = []
    for s in sources:
        if not isinstance(s, dict):
            continue
        for m in _RANGE_RE.finditer(str(s.get("value") or "")):
            a = int(m.group(1)) * 60 + int(m.group(2))
            b = int(m.group(3)) * 60 + int(m.group(4))
            if b <= a:      # 跨夜（例如 18:00–02:00）
                b += 24 * 60
            ranges.append((a, b))
        for d in s.get("closed_days") or []:
            if d not in closed:
                closed.append(d)
    return (ranges or None), closed


def _event_sort_key(e: dict) -> tuple[int, int]:
    return (e.get("day") or 0, to_min(e.get("time")) or 0)


def check_schedule(
    trip: dict,
    moves: list[dict] | None = None,
) -> dict:
    """檢查一份 trip（與一批「打算這樣改」的異動）。

    `moves` 每筆是 `{"event_id": "e12", "to_day": 3, "to_time": "16:30"}`，
    代表「我想把這個項目搬到這裡」。**不會真的搬**——只是拿來問「這樣搬會撞到什麼」。

    回傳
        {"conflicts": [...], "unverified": [...], "ok": bool, "summary": str}
    每筆 conflict 都有 `options`：要解掉它，可以犧牲什麼。
    """
    conflicts: list[dict] = []
    unverified: list[dict] = []

    events = [e for e in (trip.get("events") or []) if isinstance(e, dict)]
    by_id = {e.get("id"): e for e in events}
    places = _places(trip)
    days = _days(trip)
    n_days = day_count(trip)
    lodging = (trip.get("lodging") or [{}])[0] if trip.get("lodging") else {}

    def add(kind, event_id, what, options, **extra):
        conflicts.append({
            "kind": kind, "event_id": event_id, "what": what,
            "options": options, **extra,
        })

    # ── 1. 鎖定不可動 ──
    # 在「套用異動」之前先檢查，因為被擋下來的異動不該再拿去算後面的衝突。
    applied: dict[str, dict] = {}
    for mv in moves or []:
        eid = mv.get("event_id")
        ev = by_id.get(eid)
        if ev is None:
            add("unknown_event", eid, f"找不到 id 是 {eid!r} 的行程項目",
                ["確認 id 是不是打錯了", "先用 read_trip 看一次目前有哪些項目"])
            continue
        if ev.get("locked") or ev.get("sunset_locked"):
            why = "已訂位／已預約（locked）" if ev.get("locked") else "鎖在日落前（sunset_locked）"
            add("locked", eid,
                f"「{ev.get('title')}」是{why}，不能移動",
                [
                    f"取消或改期「{ev.get('title')}」的預約，再把 locked 拿掉",
                    "把要讓路的其他項目往後排",
                    "放棄這次移動",
                ])
            continue
        new = dict(ev)
        if mv.get("to_day") is not None:
            new["day"] = mv["to_day"]
        if mv.get("to_time"):
            new["time"] = mv["to_time"]
        applied[eid] = new

    # 要檢查的是「套用可行異動之後」的樣子
    effective = [applied.get(e.get("id"), e) for e in events]

    for e in effective:
        d = e.get("day")
        if isinstance(d, int) and n_days > 0 and not 1 <= d <= n_days:
            add("out_of_range", e.get("id"),
                f"「{e.get('title')}」被排到第 {d} 天，但這趟只有 {n_days} 天",
                [f"改排到 1..{n_days} 之間", "延長旅程日期"])

    # ── 2. 營業時間 ──
    for e in effective:
        pid = e.get("place_id")
        place = places.get(pid)
        if place is None:
            continue
        # 開放街區、公園沒有營業時間——既不該報衝突，也不該進 unverified
        if place.get("kind") in HOURS_IRRELEVANT_KINDS:
            continue
        start = to_min(e.get("time"))
        if start is None:
            continue
        end = start + (e.get("dur_min") or 0)
        ranges, closed = _hours_ranges(place)
        day_n = e.get("day")
        dt = day_date(trip, day_n) if isinstance(day_n, int) else None

        if dt is not None and closed and _WEEKDAY_KEYS[dt.weekday()] in closed:
            add("hours", e.get("id"),
                f"「{place.get('name')}」{dt.isoformat()}（{_WEEKDAY_KEYS[dt.weekday()]}）公休，"
                f"但行程排在這天 {e.get('time')}",
                [
                    "換一天去",
                    f"換一家店，放棄「{place.get('name')}」",
                    "到現場前先打電話確認是不是真的休",
                ], place_id=pid)
            continue

        if ranges is None:
            unverified.append({
                "kind": "hours_unknown", "event_id": e.get("id"), "place_id": pid,
                "what": f"「{place.get('name')}」的營業時間沒有查證過，無法判斷 {e.get('time')} 有沒有開",
                "source_hint": "Naver Map／店家官方 IG",
            })
            continue

        if not any(a <= start and end <= b for a, b in ranges):
            windows = "、".join(f"{_fmt(a)}–{_fmt(b % (24 * 60))}" for a, b in ranges)
            add("hours", e.get("id"),
                f"「{place.get('name')}」的營業時間是 {windows}，"
                f"蓋不住排定的 {e.get('time')}–{_fmt(end % (24 * 60))}",
                [
                    f"把這一項移到 {windows} 之內（要看前後行程讓不讓）",
                    f"縮短停留時間（目前 {e.get('dur_min')} 分）",
                    f"換一家店，放棄「{place.get('name')}」",
                ], place_id=pid)

    # ── 3. 交通時間吃掉停留時長 ──
    for day_n in range(1, max(n_days, 0) + 1):
        same_day = sorted(
            [e for e in effective if e.get("day") == day_n and to_min(e.get("time")) is not None],
            key=_event_sort_key,
        )
        for cur, nxt in zip(same_day, same_day[1:], strict=False):
            need = cur.get("min_dur_min")
            if not need:
                continue
            gap = (to_min(nxt["time"]) or 0) - (to_min(cur["time"]) or 0)
            leg = find_leg(trip, cur.get("place_id"), nxt.get("place_id"), day_n)
            travel = (leg or {}).get("min") or 0
            available = gap - travel
            if available < need:
                add("dwell", cur.get("id"),
                    f"「{cur.get('title')}」要留 {need} 分，"
                    f"但到下一站「{nxt.get('title')}」只剩 {available} 分"
                    f"（間隔 {gap} 分，扣掉交通 {travel} 分）",
                    [
                        f"把「{nxt.get('title')}」往後推 {need - available} 分",
                        f"把「{cur.get('title')}」的 min_dur_min 降到 {max(available, 0)} 分",
                        f"這天拿掉「{nxt.get('title')}」",
                    ], next_event_id=nxt.get("id"))

    # ── 4. 夜間動線 ──
    for day_n in range(1, max(n_days, 0) + 1):
        same_day = sorted(
            [e for e in effective if e.get("day") == day_n and to_min(e.get("time")) is not None],
            key=_event_sort_key,
        )
        if not same_day:
            continue
        late = [e for e in same_day if (to_min(e["time"]) or 0) >= NIGHT_HOUR * 60]
        if not late:
            continue
        # 跨區＝前後兩站的 area 不同
        crossed = []
        for cur, nxt in zip(same_day, same_day[1:], strict=False):
            if (to_min(nxt["time"]) or 0) < NIGHT_HOUR * 60:
                continue
            a = (places.get(cur.get("place_id")) or {}).get("area")
            b = (places.get(nxt.get("place_id")) or {}).get("area")
            if a and b and a != b:
                crossed.append((cur, nxt, a, b))
        if not crossed:
            continue
        last = same_day[-1]
        last_place = places.get(last.get("place_id")) or {}
        last_station = (last_place.get("location") or {}).get("station")
        # 「在旅館步行範圍」的判準是**最後一站與旅館同一個車站**，不是 location.walk_min——
        # 那個欄位講的是「從車站走到店」，跟「從店走回旅館」是兩回事，拿來用會誤判。
        near_hotel = (
            last.get("place_id") in ("hotel", "home")
            or (last_station and lodging.get("station") and last_station == lodging["station"])
        )
        if near_hotel:
            continue
        cur, nxt, a, b = crossed[0]
        add("night", nxt.get("id"),
            f"第 {day_n} 天 {nxt.get('time')} 之後還要從「{a}」跨到「{b}」，"
            f"而最後一站「{last.get('title')}」"
            f"（{last_station or '未記車站'}）不在旅館（{lodging.get('station') or '未記車站'}）"
            "的步行範圍內",
            [
                "把跨區那一段移到白天",
                "最後一站改成旅館附近的店",
                "接受這天晚上要搭車回旅館（末班車時間先查）",
            ], day=day_n)

    # ── 5. 日落 ──
    for e in effective:
        if not e.get("sunset_locked"):
            continue
        day_n = e.get("day")
        sunset = (days.get(day_n) or {}).get("sunset")
        arrive = to_min(e.get("time"))
        if not sunset or arrive is None:
            unverified.append({
                "kind": "sunset_unknown", "event_id": e.get("id"),
                "what": f"「{e.get('title')}」鎖在日落前，但第 {day_n} 天沒有記日落時間",
                "source_hint": "當地氣象單位或 timeanddate.com；填進 days[].sunset",
            })
            continue
        deadline = (to_min(sunset) or 0) - SUNSET_LEAD_MIN
        if arrive > deadline:
            add("sunset", e.get("id"),
                f"「{e.get('title')}」要在日落（{sunset}）前 {SUNSET_LEAD_MIN} 分、"
                f"也就是 {_fmt(deadline)} 之前到，但目前排 {e.get('time')}",
                [
                    f"把前一段行程提早 {arrive - deadline} 分",
                    "砍掉前一站，直接過來",
                    "放棄看日落，把 sunset_locked 拿掉",
                ], day=day_n)

    if conflicts:
        summary = (
            f"{len(conflicts)} 個衝突要你決定。"
            "每一個都列了「要解掉它得犧牲什麼」，我不會自己動行程。"
        )
    elif unverified:
        summary = f"沒有偵測到衝突，但有 {len(unverified)} 件事查不到資料，無法保證。"
    else:
        summary = "沒有偵測到衝突。"

    return {
        "ok": not conflicts,
        "conflicts": conflicts,
        "unverified": unverified,
        "summary": summary,
    }
