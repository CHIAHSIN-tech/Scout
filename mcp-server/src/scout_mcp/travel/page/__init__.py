"""渲染器：`render(trip: dict) -> str`。簽章由 N1 凍結（schema.RENDER_SIGNATURE）。

**這一層只渲染資料，不生成內容。** 頁面上出現的每一個店名都來自 `trip.json` 的
`places[].name`，沒有第二個來源——這是把參考產品踩過的「AI 自己多加了幾家店」
變成結構上不可能（A8）。

**同一筆資訊在頁面上出現在很多地方，全部由同一份資料算出來。**
改一個 event 的時間或天數，下面五塊會一起變（A7）：
    當日時間軸／當日標題摘要／快捷 nav 的日期標籤／地圖的文字轉乘表／正餐一覽表
參考產品那次最大的成本就是「同一筆資訊出現在 13 個地方，改一個漏改一處」，
而且是使用者發現的。這裡讓「漏改」在結構上不可能發生。

**輸出是決定性的。** 沒有時間戳、沒有亂數、沒有集合迭代順序的依賴——
同樣的 trip.json 建兩次必須位元相同（A7 的後半）。

**輸出是自含單檔。** 沒有外部 script／樣式表／字體／圖片，沒有 fetch。
唯一允許出現外部網址的位置是 `<a href>`（地圖導航與來源連結）。斷網打得開（A9）。
"""

from __future__ import annotations

import html
import json

from ..schema import HOURS_IRRELEVANT_KINDS, RESERVED_PLACE_IDS, day_count, day_date, find_leg
from .css import CSS
from .js import JS

E = html.escape

# 星期幾。day_date() 回的是 date，weekday() 0=週一。
_DOW = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
_DOW_KEY = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# 每天一個顏色。超過五天就循環——顏色是用來分辨相鄰兩天，不是唯一識別。
_DAY_COLORS = ["var(--d1)", "var(--d2)", "var(--d3)", "var(--d4)", "var(--d5)"]

# 地鐵線號的顏色。首爾的沿用參考產品實測過的官方色；其他城市沒有資料時
# 一律用中性灰——**不猜**一個顏色，猜錯會讓人在現場找錯月台。
LINE_COLORS = {
    "1": ["#0052A4", "#fff"], "2": ["#00A84D", "#fff"], "3": ["#EF7C1C", "#1a1a1a"],
    "4": ["#00A5DE", "#fff"], "5": ["#996CAC", "#fff"], "6": ["#CD7C2F", "#fff"],
    "7": ["#747F00", "#fff"], "8": ["#E6186C", "#fff"], "9": ["#BDB092", "#1a1a1a"],
    "A": ["#0090D2", "#fff"], "水": ["#F5A200", "#1a1a1a"],
}

_RESV_LABEL = {
    "walkin": "現場排", "advance": "需訂位", "hard": "難訂", "unknown": "訂位方式不明",
}

_TYPE_LABEL = {
    "meal": "用餐", "shopping": "購物", "sight": "景點", "service": "預約", "move": "移動",
}


# ── 小工具 ────────────────────────────────────────────────────────────

def _places(trip):
    return {p["id"]: p for p in (trip.get("places") or []) if isinstance(p, dict) and p.get("id")}


def _days_meta(trip):
    return {d["day"]: d for d in (trip.get("days") or []) if isinstance(d, dict) and "day" in d}


def _events_of(trip, day):
    evs = [e for e in (trip.get("events") or []) if isinstance(e, dict) and e.get("day") == day]
    return sorted(evs, key=lambda e: (str(e.get("time") or ""), str(e.get("id") or "")))


def _md(trip, day):
    """`9/23`。算不出來時回空字串，不編一個日期。"""
    d = day_date(trip, day)
    return f"{d.month}/{d.day}" if d else ""


def pn(place, fallback=""):
    """地點名。**頁面上每一個店名都得走這個函式**——驗收腳本靠 class="pn" 確認
    頁面沒有 trip.json 以外的店（A8）。"""
    if not place:
        return E(fallback)
    return f'<span class="pn" data-place="{E(place["id"])}">{E(place.get("name") or "")}</span>'


def _ln(name):
    c = LINE_COLORS.get(str(name), ["#8A92A3", "#fff"])
    dk = " dk" if c[1] != "#fff" else ""
    return f'<span class="ln{dk}" style="--c:{c[0]}">{E(str(name))}</span>'


def _links(items):
    """`[{label, url}]` → 一排連結。外部網址只會出現在這裡（A9 的唯一例外）。"""
    out = []
    for it in items or []:
        if isinstance(it, dict) and it.get("url"):
            label = it.get("label") or "連結"
            out.append(f'<a href="{E(it["url"])}" target="_blank" rel="noopener">{E(label)}</a>')
    return "".join(out)


def _notes_html(notes, limit=140):
    """店家註記。太長的收進 `<details>`，預設摺起來。

    為什麼需要：從 `rest.json` 轉進來的 `notes` 是查證過程的研究筆記，
    動輒好幾百字（公休日來源互相矛盾的推論、價位帶怎麼取捨…）。
    那些內容有價值、不能丟，但整段攤在候補卡片上會把清單變成一面文字牆。
    用 `<details>` 不用 JS——自含單檔不該為了摺疊多一段腳本。
    """
    if not notes:
        return ""
    text = str(notes)
    if len(text) <= limit:
        return f'<p class="fit">{E(text)}</p>'
    head = text[:limit].rstrip()
    return (
        f'<details class="longnote"><summary>{E(head)}…</summary>'
        f'<p class="fit">{E(text)}</p></details>'
    )


def _hours_html(place):
    """營業時間。三種狀態各有不同輸出，**留白不是其中之一**——
    留白會被讀成「沒有營業時間限制」，那正是我們要避免的誤導。

    唯一的例外是 `kind: "area"`（開放街區、公園）：它本來就沒有營業時間，
    印「尚未查證」會變成一個永遠查不完的假待辦。
    """
    if place.get("kind") in HOURS_IRRELEVANT_KINDS:
        return ""
    sources = ((place.get("hours") or {}).get("sources")) or []
    values, urls = [], []
    for s in sources:
        if not isinstance(s, dict):
            continue
        v = s.get("value")
        if v is not None and v not in values:
            values.append(v)
            urls.append(s.get("url"))
    if not values:
        # A12：沒查證就明說沒查證，不印時間
        return '<p class="unverified">營業時間尚未查證（見「出發前待確認」）</p>'
    if len(values) == 1:
        return f'<p class="meta">{E(str(values[0]))}</p>'
    # A13：兩個都印、標出衝突，不挑一個當正確答案
    rows = "".join(
        f'<span class="cv">{E(str(v))}'
        + (f'　<a href="{E(u)}" target="_blank" rel="noopener">來源</a>' if u else "")
        + "</span>"
        for v, u in zip(values, urls, strict=False)
    )
    return (
        '<div class="conflict"><span class="cmark">來源互相矛盾，兩個都列出來</span>'
        + rows + "</div>"
    )


# ── 各區塊 ────────────────────────────────────────────────────────────

def _day_summary(trip, day):
    """當日摘要：由當天的 events 算出來，不是人寫的標題。

    A7 的連動點之一——改一個 event 的時間或天數，這行一定跟著變。
    """
    evs = _events_of(trip, day)
    if not evs:
        return "這天還沒有安排"
    return " → ".join(f"{e.get('time')} {e.get('title')}" for e in evs)


def _header(trip):
    meta = trip.get("trip") or {}
    n = day_count(trip)
    bits = []
    if meta.get("party_size"):
        bits.append(f"{meta['party_size']} 人")
    if n:
        bits.append(f"{n - 1} 晚 {n} 天")
    if meta.get("country_name") or meta.get("city_name"):
        bits.append(E(meta.get("city_name") or meta.get("country_name")))
    eyebrow = "<span>·</span>".join(f"<span>{E(b)}</span>" for b in bits)

    flights = ""
    for f in trip.get("flights") or []:
        if not isinstance(f, dict):
            continue
        d = f.get("date") or ""
        dow = ""
        try:
            from datetime import date as _d
            dow = _DOW[_d.fromisoformat(d).weekday()]
        except ValueError:
            dow = ""
        when = ""
        if f.get("dep") or f.get("arr"):
            when = f"{f.get('dep') or ''}–{f.get('arr') or ''}"
            if f.get("arr_next_day"):
                when += "<sup>+1</sup>"
        note = f'<p class="note">{E(f["note"])}</p>' if f.get("note") else ""
        flights += (
            '<div class="flight" role="listitem">'
            f'<div class="d"><strong>{E(d[5:].replace("-", "/") if len(d) >= 10 else d)}</strong>{E(dow)}</div>'
            f'<div class="r">{E(f.get("from") or "")} <i>→</i> {E(f.get("to") or "")}'
            + (f' <i>{E(f["no"])}</i>' if f.get("no") else "")
            + "</div>"
            f'<div class="t">{when}</div>{note}</div>'
        )
    flights_html = f'<div class="flights" role="list">{flights}</div>' if flights else ""

    lede = f'<p class="lede">{E(meta.get("notes"))}</p>' if meta.get("notes") else ""
    return (
        "<header>"
        f'<div class="eyebrow">{eyebrow}</div>'
        f'<h1>{E(meta.get("title") or "")}</h1>'
        f"{lede}{flights_html}</header>"
    )


def _nav(trip):
    """快捷 nav。標籤含「日期 ＋ 當天項目數」——項目數是 A7 的保險：
    只要有項目換了天，兩天的標籤都會變。"""
    n = day_count(trip)
    dm = _days_meta(trip)
    lis = ['<li><a href="#eat">訂好的</a></li>']
    for d in range(1, n + 1):
        evs = _events_of(trip, d)
        title = (dm.get(d) or {}).get("subtitle") or (dm.get(d) or {}).get("title") or ""
        short = E(title[:12])
        lis.append(
            f'<li><a href="#d{d}"><span>{E(_md(trip, d))}</span>{short}'
            f'<i class="cnt">{len(evs)} 項</i></a></li>'
        )
    lis.append('<li><a href="#questions">待確認</a></li>')
    return f'<nav class="days" aria-label="跳到某一段"><ul>{"".join(lis)}</ul></nav>'


def _brief(trip):
    panels = []
    for lg in trip.get("lodging") or []:
        if not isinstance(lg, dict):
            continue
        items = []
        if lg.get("station"):
            items.append(f"最近車站：{E(lg['station'])}")
        if lg.get("address"):
            items.append(E(lg["address"]))
        if lg.get("check_in") or lg.get("check_out"):
            items.append(f"{E(lg.get('check_in') or '')} → {E(lg.get('check_out') or '')}")
        if lg.get("booking_ref"):
            items.append(f"訂房編號：{E(lg['booking_ref'])}")
        if lg.get("notes"):
            items.append(E(lg["notes"]))
        panels.append(
            '<div class="panel stay"><h2>旅館：' + E(lg.get("name") or "") + "</h2><ul>"
            + "".join(f"<li>{x}</li>" for x in items) + "</ul></div>"
        )
    meta = trip.get("trip") or {}
    budget = (meta.get("budget") or {}).get("per_person_per_meal") or {}
    if budget.get("value"):
        panels.append(
            '<div class="panel moon"><h2>預算</h2><ul>'
            f'<li>每人每餐上限 {E(str(budget["value"]))} {E(str(budget.get("currency") or ""))}</li>'
            "</ul></div>"
        )
    return f'<div class="brief">{"".join(panels)}</div>' if panels else ""


def _booked_table(trip):
    """訂好的東西：班機、旅館、以及所有 locked 的事件。"""
    rows = []
    for f in trip.get("flights") or []:
        if not isinstance(f, dict):
            continue
        label = "去程" if f.get("dir") == "out" else "回程"
        detail = f"{E(f.get('date') or '')} {E(f.get('from') or '')} → {E(f.get('to') or '')}"
        if f.get("dep"):
            detail += f" {E(f['dep'])}–{E(f.get('arr') or '')}"
        rows.append(f'<tr><th scope="row">{label}</th><td>{detail}</td>'
                    f'<td><small>{"已訂" if f.get("locked") else "未確認"}</small></td></tr>')
    for lg in trip.get("lodging") or []:
        if not isinstance(lg, dict):
            continue
        rows.append(
            f'<tr><th scope="row">旅館</th><td>{E(lg.get("name") or "")}'
            + (f'（{E(lg["station"])}）' if lg.get("station") else "")
            + f'</td><td><small>{"已訂" if lg.get("locked") else "未確認"}</small></td></tr>'
        )
    places = _places(trip)
    for e in sorted((trip.get("events") or []),
                    key=lambda x: (x.get("day") or 0, str(x.get("time") or ""))):
        if not isinstance(e, dict):
            continue
        # 機場、旅館這類保留地點不算「訂位」——班機與旅館上面已經列過
        if e.get("place_id") in RESERVED_PLACE_IDS:
            continue
        p = places.get(e.get("place_id"))
        rv = (p or {}).get("reservation") or {}
        if e.get("locked"):
            status = "已訂，鎖定"
        elif rv.get("required") and not rv.get("done"):
            # 「必須訂但還沒訂」是最需要被看見的狀態
            status = '<b class="need">待預約</b>'
        else:
            continue
        rows.append(
            f'<tr><th scope="row">{E(_TYPE_LABEL.get(e.get("type") or "", "行程"))}</th>'
            f'<td>{E(_md(trip, e.get("day")))} {E(e.get("time") or "")} '
            f'{pn(p, e.get("title") or "")}</td>'
            f"<td><small>{status}</small></td></tr>"
        )
    if not rows:
        return ""
    return (
        '<h3 class="h2sub">訂好的東西</h3>'
        '<div class="tbl stack t-book"><table>'
        "<thead><tr><th>項目</th><th>內容</th><th>狀態</th></tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _meal_table(trip):
    """正餐一覽。A7 的連動點之一：每一列都帶日期與時間。"""
    places = _places(trip)
    rows = []
    for e in sorted((trip.get("events") or []),
                    key=lambda x: (x.get("day") or 0, str(x.get("time") or ""))):
        if not isinstance(e, dict):
            continue
        p = places.get(e.get("place_id"))
        is_meal = e.get("type") == "meal" or (p or {}).get("kind") == "meal"
        if not is_meal:
            continue
        band = ((p or {}).get("price_band") or {}).get("band") or "—"
        rv = (p or {}).get("reservation") or {}
        if rv.get("done"):
            status = f"已訂 {E(e.get('time') or '')}"
        elif e.get("locked"):
            status = "已訂，鎖定"
        elif rv.get("required"):
            status = _RESV_LABEL.get(rv.get("difficulty") or "unknown", "需訂位")
        else:
            status = "機動"
        cuisine = "／".join((p or {}).get("cuisine") or [])[:20]
        rows.append(
            f'<tr><th scope="row">{E(_md(trip, e.get("day")))} {E(e.get("time") or "")}</th>'
            f'<td>{pn(p, e.get("title") or "")} <small>{E(cuisine)}</small></td>'
            f'<td class="bdc">{E(band)}</td><td><small>{status}</small></td></tr>'
        )
    if not rows:
        return ""
    return (
        '<h3 class="h2sub">正餐</h3>'
        '<div class="tbl stack t-meal"><table>'
        "<thead><tr><th>餐</th><th>店／菜系</th><th>價位</th><th>狀態</th></tr></thead>"
        f'<tbody id="meal-rows">{"".join(rows)}</tbody></table></div>'
        '<div class="legend">'
        + " ".join(f'<span class="rs {k}">{E(v)}</span>' for k, v in _RESV_LABEL.items())
        + "</div>"
    )


def _timeline(trip, day):
    """一天的時間軸。行程項目、交通、餐點都在這裡，順序由時間決定。"""
    places = _places(trip)
    evs = _events_of(trip, day)
    out = []
    last_pid = None
    for i, e in enumerate(evs):
        if e.get("place_id"):
            last_pid = e["place_id"]
        p = places.get(e.get("place_id"))
        cls = []
        if e.get("type") == "meal" or (p or {}).get("kind") == "meal":
            cls.append("meal")
        if e.get("sunset_locked"):
            cls.append("sunset")
        elif e.get("locked"):
            cls.append("hi")
        tag = ""
        if e.get("locked"):
            tag = '<span class="pick">已訂</span>'
        elif e.get("sunset_locked"):
            tag = '<span class="pick">日落前</span>'

        body = []
        if e.get("note"):
            body.append(f"<p>{E(e['note'])}</p>")
        if p:
            loc = p.get("location") or {}
            where = "・".join(
                E(x) for x in [p.get("area"), loc.get("station") and f"{loc['station']} 站",
                               loc.get("walk_min") and f"走 {loc['walk_min']} 分"] if x)
            # 地點名一定印在這一行：標題是人寫的（「午餐：Mamalee」「晚餐（機動）」），
            # 店名得另外出現，驗收才找得到它來自 places（A8）
            body.append(f'<p class="meta">{pn(p)}{"・" + where if where else ""}</p>')
            body.append(_hours_html(p))
            pb = p.get("price_band") or {}
            if pb.get("band") or pb.get("note"):
                body.append(
                    f'<p class="meta"><span class="bd">{E(pb.get("band") or "")}</span> '
                    f'{E(pb.get("note") or "")}</p>')
            alert = p.get("alert")
            if isinstance(alert, dict):
                body.append(f'<div class="warnbox"><b>注意：</b>{E(alert.get("text") or "")}</div>')
            elif alert:
                body.append(f'<div class="warnbox"><b>注意：</b>{E(str(alert))}</div>')

        link_items = list(e.get("links") or [])
        if p:
            loc = p.get("location") or {}
            if loc.get("map_url"):
                link_items.append({"label": "地圖", "url": loc["map_url"]})
            rv = p.get("reservation") or {}
            if rv.get("url"):
                link_items.append({"label": "訂位", "url": rv["url"]})
            for s in p.get("sources") or []:
                link_items.append({"label": "來源", "url": s})
        links = _links(link_items)
        links_html = f'<div class="links">{links}</div>' if links else ""

        # 標題用事件自己的標題，不換成店名——「晚餐（機動）」「The Hyundai 第 2 段」
        # 這種標題本身就是資訊，換成店名會把它吃掉
        title = E(e.get("title") or "")
        out.append(
            f'    <li class="{" ".join(cls)}"><time>{E(e.get("time") or "")}</time><div class="b">\n'
            f"      <h3>{title} {tag}</h3>\n"
            f'      {"".join(body)}{links_html}\n    </div></li>\n'
        )

        # 兩站之間的交通（有 leg 資料才畫）
        # 沒有地點的事件（例如「晚餐（機動）」）不打斷交通段：
        # 用「最近一個有地點的事件」接下一站
        if i + 1 < len(evs):
            g = find_leg(trip, last_pid, evs[i + 1].get("place_id"), day)
            if g:
                lines = "".join(_ln(x) for x in (g.get("lines") or []))
                txt = g.get("label") or ""
                if not txt:
                    bits = []
                    if g.get("transfer_at"):
                        bits.append("轉 " + "、".join(str(t) for t in g["transfer_at"]))
                    if g.get("min"):
                        bits.append(f"約 {g['min']} 分")
                    txt = "，".join(bits)
                out.append(
                    f'    <li class="mv"><time></time><div class="b route">{lines} {E(txt)}</div></li>\n'
                )
    return "".join(out)


def _day_sections(trip):
    dm = _days_meta(trip)
    n = day_count(trip)
    out = []
    for d in range(1, n + 1):
        meta = dm.get(d) or {}
        dt = day_date(trip, d)
        dow = _DOW[dt.weekday()] if dt else ""
        chips = "".join(f'<span class="chip">{E(str(c))}</span>' for c in (meta.get("chips") or []))
        if meta.get("sunset"):
            chips += f'<span class="chip sun">日落 約 {E(meta["sunset"])}</span>'
        warn = f'<div class="warnbox"><b>提醒：</b>{E(meta["warn"])}</div>' if meta.get("warn") else ""
        out.append(
            f'<section class="day" id="d{d}">\n'
            '  <div class="dayhead">\n'
            f'    <div class="date"><small>{E(dow)} · DAY {d}</small>{E(_md(trip, d))}</div>\n'
            f'    <h2>{E(meta.get("title") or f"第 {d} 天")}</h2>\n'
            f'    <div class="tags">{chips}</div>\n'
            f'    <p class="daysum">{E(_day_summary(trip, d))}</p>\n'
            "  </div>\n"
            f"  {warn}\n  <ol class=\"tl\">\n{_timeline(trip, d)}  </ol>\n</section>\n"
        )
    return "".join(out)


def _questions(trip):
    qs = [q for q in (trip.get("open_questions") or []) if isinstance(q, dict)]
    qs.sort(key=lambda q: (str(q.get("check_by") or "9999"), str(q.get("id") or "")))
    if not qs:
        return ""
    lis = []
    for q in qs:
        auto = '<span class="autotag">自動偵測</span>' if q.get("auto") else ""
        sub = []
        if q.get("why"):
            sub.append(E(q["why"]))
        if q.get("check_by"):
            sub.append(f"{E(q['check_by'])} 前確認")
        if q.get("source_hint"):
            sub.append(f"查：{E(q['source_hint'])}")
        lis.append(
            f'<li><label for="q-{E(q.get("id") or "")}">'
            f'<input type="checkbox" id="q-{E(q.get("id") or "")}">'
            f'<span>{E(q.get("what") or "")}{auto}'
            + (f"<small>{'・'.join(sub)}</small>" if sub else "")
            + "</span></label></li>"
        )
    return (
        '<section class="block" id="questions"><h2>出發前待確認</h2>'
        f'<ul class="check">{"".join(lis)}</ul></section>'
    )


def _queue_list(trip):
    """排隊候補：queue_only 的店只在這裡出現，不進時間軸。"""
    qs = [p for p in (trip.get("places") or [])
          if isinstance(p, dict) and p.get("queue_only")]
    # 照 places 陣列的順序——那是人排的優先順序；陣列順序本身就是決定性的
    if not qs:
        return ""
    cards = []
    for p in qs:
        loc = p.get("location") or {}
        links = _links(
            ([{"label": "地圖", "url": loc["map_url"]}] if loc.get("map_url") else [])
            + ([{"label": "訂位", "url": (p.get("reservation") or {}).get("url")}]
               if (p.get("reservation") or {}).get("url") else [])
        )
        band = (p.get("price_band") or {}).get("band") or ""
        diff = (p.get("reservation") or {}).get("difficulty") or "unknown"
        cards.append(
            '<div class="opt">'
            f'<div class="oh"><strong>{pn(p)}</strong><span class="tags2">'
            f'<span class="bd">{E(band)}</span>'
            f'<span class="rs {E(diff)}">{E(_RESV_LABEL.get(diff, ""))}</span></span></div>'
            f'<p class="meta">{E(p.get("area") or "")}</p>'
            f"{_hours_html(p)}"
            + _notes_html(p.get("notes"))
            + (f'<div class="of"><span class="links">{links}</span></div>' if links else "")
            + "</div>"
        )
    return (
        '<section class="wsec" id="backup"><h2>排隊候補</h2>'
        '<p class="lede2">這些店不收訂位或以候位為主，所以不排進時間軸，'
        "只在訂位落空或剛好順路時用。</p>"
        f'<div class="qlist">{"".join(cards)}</div></section>'
    )


# ── 地圖 ──────────────────────────────────────────────────────────────

def _map_data(trip):
    """算出地圖要用的投影、地點、每日路線與文字轉乘表。

    文字轉乘表（DAYS[dN].legs）是 A7 的連動點之一——它由 events 的時間與順序算出來。
    """
    meta = trip.get("trip") or {}
    places = _places(trip)
    n = day_count(trip)
    lodging = (trip.get("lodging") or [{}])[0] if trip.get("lodging") else {}

    # 有座標的地點才畫得出來
    coords = {}
    for pid, p in places.items():
        loc = p.get("location") or {}
        if isinstance(loc.get("lat"), (int, float)) and isinstance(loc.get("lon"), (int, float)):
            coords[pid] = (loc["lat"], loc["lon"], p.get("name"), loc.get("station"))
    if isinstance(lodging.get("lat"), (int, float)) and isinstance(lodging.get("lon"), (int, float)):
        coords["hotel"] = (lodging["lat"], lodging["lon"], lodging.get("name"), lodging.get("station"))

    if not coords:
        return None

    m = trip.get("map") or {}
    lats = [c[0] for c in coords.values()]
    lons = [c[1] for c in coords.values()]
    pad_lat = max((max(lats) - min(lats)) * 0.15, 0.01)
    pad_lon = max((max(lons) - min(lons)) * 0.15, 0.01)
    proj = {
        "lon0": m.get("lon0", round(min(lons) - pad_lon, 4)),
        "lon1": m.get("lon1", round(max(lons) + pad_lon, 4)),
        "lat0": m.get("lat0", round(min(lats) - pad_lat, 4)),
        "lat1": m.get("lat1", round(max(lats) + pad_lat, 4)),
    }

    def _xy(lat, lon):
        x = (lon - proj["lon0"]) / (proj["lon1"] - proj["lon0"]) * 1000
        y = (proj["lat1"] - lat) / (proj["lat1"] - proj["lat0"]) * 640
        return x, y

    # 標籤避讓：同一區的地點座標常常只差幾十公尺，投影到示意圖上就疊在一起。
    # 這裡把「離已放好的標籤太近」的往下推一格。**不改座標，只改標籤位置**——
    # 點還是畫在原地，只有文字挪開。走 sorted 順序，所以結果是決定性的。
    P = {}
    placed: list[tuple[float, float]] = []
    for pid, (lat, lon, name, station) in sorted(coords.items()):
        x, y = _xy(lat, lon)
        right = x > 700
        dy = -8
        while any(abs(px - x) < 150 and abs(py - (y + dy)) < 26 for px, py in placed):
            dy += 26
        placed.append((x, y + dy))
        P[pid] = {
            "n": name or pid, "s": station or "", "lat": lat, "lon": lon,
            "dx": -12 if right else 12, "dy": dy,
            "a": "end" if right else "start",
            "home": 1 if pid == "hotel" else 0,
        }

    DAYS, order = {}, []
    for d in range(1, n + 1):
        evs = [e for e in _events_of(trip, d) if e.get("place_id") in P]
        if not evs:
            continue
        key = f"d{d}"
        order.append(key)
        route, seg, text = [], [], []
        for i, e in enumerate(evs):
            route.append(e["place_id"])
            text.append(f"{e.get('time')} {e.get('title')}")
            if i + 1 < len(evs):
                g = find_leg(trip, e.get("place_id"), evs[i + 1].get("place_id"), d)
                if g:
                    # 地圖上的膠囊放不下整句說明，只放分鐘數；完整文字在時間軸
                    if g.get("min"):
                        label = f"{g['min']}分"
                    else:
                        label = "計程車" if g.get("mode") == "taxi" else ""

                    seg.append({
                        "l": [str(x) for x in (g.get("lines") or [])],
                        "m": label,
                        "t": g.get("label_t", 0.5),
                        "dx": g.get("label_dx", 0),
                        "dy": g.get("label_dy", 0),
                    })
                else:
                    seg.append(None)
        DAYS[key] = {
            "c": _DAY_COLORS[(d - 1) % len(_DAY_COLORS)],
            "label": _md(trip, d),
            "r": route,
            "seg": seg,
            "legs": text,
        }

    used = {pid for k in order for pid in DAYS[k]["r"]}
    return {
        "slug": meta.get("page_slug") or "trip",
        "proj": proj,
        "river": (trip.get("map") or {}).get("river") or [],
        "P": {k: v for k, v in P.items() if k in used},
        "DAYS": DAYS,
        "order": order,
        "lineColors": LINE_COLORS,
        "home": [coords["hotel"][0], coords["hotel"][1]] if "hotel" in coords else None,
    }


def _map_tab(trip, mapdata):
    if not mapdata:
        return ('<div id="tab-map" hidden><section class="block mapsec">'
                "<h2>地圖</h2><p class=\"lede2\">還沒有任何地點有經緯度，畫不出示意圖。"
                "用 upsert_place 補上 location.lat／location.lon 之後重新建置。</p>"
                f"{_queue_list(trip)}</section></div>")
    btns = '<button type="button" data-day="all" aria-pressed="true">全部</button>'
    for k in mapdata["order"]:
        d = mapdata["DAYS"][k]
        btns += (f'<button type="button" data-day="{E(k)}" aria-pressed="false">'
                 f'<i style="background:{E(d["c"])}"></i>{E(d["label"])}</button>')
    return (
        '<div id="tab-map" hidden>'
        '<section class="block mapsec" id="mapsec">'
        "<h2>地圖</h2>"
        '<p class="lede2">示意圖，位置大約、比例不精準；線是「這天去的順序」，'
        "不是實際的地鐵路線。點日期看那天的轉乘。</p>"
        f'<div class="dayfilter" role="group" aria-label="選日期">{btns}</div>'
        '<div class="mapbox"><svg id="map-svg" viewBox="0 0 1000 640" role="img" '
        'aria-label="行程示意地圖"></svg></div>'
        '<p class="panhint">地圖可以左右、上下滑動。</p>'
        '<div id="map-legs" class="legs"></div>'
        f"{_queue_list(trip)}"
        "</section></div>"
    )


# ── 其他分頁 ──────────────────────────────────────────────────────────

def _stations_block(trip):
    rows = []
    for s in trip.get("stations") or []:
        if not isinstance(s, dict):
            continue
        lines = "".join(_ln(x) for x in (s.get("lines") or []))
        days = "、".join(str(d) for d in (s.get("days") or []))
        # 欄位順序**必須**是 English / 當地 / 中文 / 線 / 第幾天。
        # 移植過來的 `.t-stn` 手機版規則是用 nth-child 寫的（參考產品就是這個順序）：
        # 英文名獨佔第一行、線號靠右貼著它，當地名與中文名折到第二行、哪天用推到最右。
        # 換順序不會報錯，只會讓手機上的排版錯開——第一次就是這樣才發現的。
        rows.append(
            f'<tr><th scope="row">{E(s.get("en") or "")}</th>'
            f'<td>{E(s.get("local") or "")}</td>'
            f'<td>{E(s.get("zh") or "")}</td>'
            f'<td class="lines">{lines}</td>'
            f"<td><small>{E(days)}</small></td></tr>"
        )
    if not rows:
        return None
    return (
        '<section class="block" id="stations"><h2>車站對照</h2>'
        '<p class="lede2">站名以英文為主——現場招牌與地圖 App 的英文介面都是這個。</p>'
        '<div class="tbl stack t-stn"><table>'
        "<thead><tr><th>English</th><th>當地</th><th>中文</th><th>線</th><th>第幾天</th></tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _section_block(key, sec):
    """`sections` 的一塊。有資料才渲染——沒有藥局資料就不該出現空的藥局分頁。"""
    title = sec.get("title") or key
    parts = []
    for b in sec.get("blocks") or []:
        if not isinstance(b, dict):
            continue
        h = f'<h3>{E(b["heading"])}</h3>' if b.get("heading") else ""
        body = f"<p>{E(b['text'])}</p>" if b.get("text") else ""
        items = "".join(f"<li>{E(str(x))}</li>" for x in (b.get("items") or []))
        parts.append(f'<div class="qa">{h}{body}{f"<ul>{items}</ul>" if items else ""}</div>')
    for name in ("todos", "packing"):
        if sec.get(name):
            # 每一項可以是字串、{text, done}（已做完的預先打勾），
            # 或 {group, items}（分組標題＋底下的項目，沿用參考產品的 .check li.cg 樣式）
            parts_li, n = [], 0
            for x in sec[name]:
                if isinstance(x, dict) and "group" in x:
                    parts_li.append(f'<li class="cg">{E(str(x["group"]))}</li>')
                    entries = x.get("items") or []
                else:
                    entries = [x]
                for it in entries:
                    text = it.get("text") if isinstance(it, dict) else it
                    done = " checked" if isinstance(it, dict) and it.get("done") else ""
                    parts_li.append(
                        f'<li><label for="{E(key)}-{name}-{n}">'
                        f'<input type="checkbox" id="{E(key)}-{name}-{n}"{done}>'
                        f"<span>{E(str(text))}</span></label></li>")
                    n += 1
            lis = "".join(parts_li)
            label = "待辦" if name == "todos" else "打包"
            parts.append(f'<h3 class="h2sub">{label}</h3><ul class="check">{lis}</ul>')
    if not parts:
        return None
    return f'<section class="block" id="{E(key)}"><h2>{E(title)}</h2>{"".join(parts)}</section>'


def _more_tab(trip):
    blocks = []
    st = _stations_block(trip)
    if st:
        blocks.append(("stations", "車站", st))
    for key in sorted((trip.get("sections") or {})):
        sec = (trip.get("sections") or {})[key]
        if not isinstance(sec, dict):
            continue
        b = _section_block(key, sec)
        if b:
            blocks.append((key, sec.get("title") or key, b))
    if not blocks:
        return ""
    subs = "".join(
        f'<button type="button" role="tab" data-sub="{E(k)}" '
        f'aria-selected="{"true" if i == 0 else "false"}">{E(label)}</button>'
        for i, (k, label, _) in enumerate(blocks)
    )
    return (
        '<div id="tab-more" hidden>'
        f'<div class="subtabs" role="tablist" aria-label="其他">{subs}</div>'
        + "".join(b for _, _, b in blocks)
        + "</div>"
    )


# ── 組裝 ──────────────────────────────────────────────────────────────

def render(trip: dict) -> str:
    """trip.json → 自含單檔 HTML。簽章由 schema.RENDER_SIGNATURE 凍結。"""
    meta = trip.get("trip") or {}
    title = meta.get("title") or "行程表"
    mapdata = _map_data(trip)

    tabs = ['<button type="button" role="tab" data-tab="plan" aria-selected="true">行程</button>',
            '<button type="button" role="tab" data-tab="map" aria-selected="false">地圖</button>']
    more = _more_tab(trip)
    if more:
        tabs.append('<button type="button" role="tab" data-tab="more" aria-selected="false">其他</button>')

    plan = (
        '<div id="tab-plan">'
        + _nav(trip)
        + _brief(trip)
        + '<section class="dining" id="eat"><h2>總覽</h2>'
        + _booked_table(trip) + _meal_table(trip) + "</section>"
        + _day_sections(trip)
        + _questions(trip)
        + "</div>"
    )

    # MAPDATA 一定要有值：JS 三段都讀 MAPDATA.slug，沒有地圖資料時也得給個空殼。
    payload = mapdata or {
        "slug": meta.get("page_slug") or "trip",
        "proj": {}, "river": [], "P": {}, "DAYS": {}, "order": [],
        "lineColors": LINE_COLORS, "home": None,
    }
    # sort_keys：JSON 的鍵序固定，建兩次才會位元相同（A7）
    data_js = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    doc = (
        "<!DOCTYPE html>\n"
        '<html lang="zh-Hant">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{E(title)}</title>\n"
        f"<style>\n{CSS}\n</style>\n"
        "</head>\n<body>\n"
        '<div class="wrap">\n'
        + _header(trip)
        + f'<div class="tabs" role="tablist">{"".join(tabs)}</div>\n'
        + plan
        + _map_tab(trip, mapdata)
        + more
        + "\n</div>\n"
        + "<script>\nvar MAPDATA = " + data_js + ";\n" + JS + "\n</script>\n"
        + "</body>\n</html>\n"
    )

    # 移植自參考產品 build2.py 最後一行的 `assert '{{' not in t`：
    # 模板沒填完就直接爆，而不是把 {{placeholder}} 印在使用者的頁面上。
    assert "{{" not in doc, "模板有沒填完的 placeholder"
    return doc
