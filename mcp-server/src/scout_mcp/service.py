"""工具的實際邏輯。

與 MCP 註冊分開的理由：這一層只依賴 `PostgrestClient` 這個介面，
所以離線測試可以直接餵 fake client 進來，不必啟動 MCP server（spec AC-7）。

每個函式都回傳「一句人話摘要 ＋ structured payload」的模型（spec §5 pattern 7）。
摘要是給人／agent 一眼看懂的結論，payload 是完整資料。
"""

from __future__ import annotations

from typing import Any

from .contracts import (
    BuylistItem,
    BuylistItemResult,
    BuylistItemsResult,
    ItineraryItem,
    ItineraryItemResult,
    ItineraryItemsResult,
    Trip,
    TripResult,
    TripsResult,
    parse_row,
    parse_rows,
    require_any_field,
    validate_day_number,
    validate_start_time,
)
from .errors import retry_pointless
from .rest import PostgrestClient

TRIPS = "trips"
ITEMS = "itinerary_items"
BUYLIST = "buylist_items"


def _where_id(value: int) -> dict[str, str]:
    return {"id": f"eq.{value}"}


async def _get_trip(client: PostgrestClient, trip_id: int) -> Trip:
    rows = await client.select(TRIPS, {"select": "*", **_where_id(trip_id)})
    return parse_row(Trip, rows, f"旅程（trip_id={trip_id}）")


# ══════════════════════════════════════════════════════════
#  行程
# ══════════════════════════════════════════════════════════


async def list_trips(client: PostgrestClient) -> TripsResult:
    rows = await client.select(TRIPS, {"select": "*", "order": "start_date.desc"})
    trips = parse_rows(Trip, rows, "旅程清單")
    if not trips:
        return TripsResult(summary="目前一趟旅程都沒有。可以用 create_trip 建立第一趟。", trips=[])
    head = "、".join(f"{t.name}（{t.start_date} ~ {t.end_date}）" for t in trips[:3])
    more = f"，另有 {len(trips) - 3} 趟" if len(trips) > 3 else ""
    return TripsResult(summary=f"共 {len(trips)} 趟旅程：{head}{more}。", trips=trips)


async def create_trip(
    client: PostgrestClient,
    username: str,
    name: str,
    start_date: str,
    end_date: str,
    notes: str | None = None,
) -> TripResult:
    if end_date < start_date:
        raise retry_pointless(
            f"結束日期 {end_date} 早於開始日期 {start_date}。",
            "確認兩個日期是不是寫反了，改成 end_date >= start_date 再送一次。",
        )
    row = await client.insert(
        TRIPS,
        {
            "username": username,
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "notes": notes or "",
        },
    )
    trip = parse_row(Trip, [row], "新建立的旅程")
    return TripResult(
        summary=f"已建立旅程「{trip.name}」（{trip.start_date} ~ {trip.end_date}，共 {trip.total_days} 天）。",
        trip=trip,
    )


async def list_itinerary_items(
    client: PostgrestClient,
    trip_id: int,
    day_number: int | None = None,
    only_candidates: bool = False,
    only_unconfirmed: bool = False,
) -> ItineraryItemsResult:
    if day_number is not None and only_candidates:
        raise retry_pointless(
            "同時指定了 day_number 與 only_candidates，這兩個條件互相矛盾"
            "——候選項目的定義就是還沒有 day_number。",
            "想看某一天就只給 day_number；想看還沒排的就只給 only_candidates=true。",
        )

    params: dict[str, str] = {
        "select": "*",
        "trip_id": f"eq.{trip_id}",
        "order": "day_number.asc,start_time.asc",
    }
    if only_candidates:
        params["day_number"] = "is.null"
    elif day_number is not None:
        trip = await _get_trip(client, trip_id)
        validate_day_number(day_number, trip)
        params["day_number"] = f"eq.{day_number}"
    if only_unconfirmed:
        params["is_confirmed"] = "eq.false"

    rows = await client.select(ITEMS, params)
    items = parse_rows(ItineraryItem, rows, "行程項目")

    scope = "候選項目" if only_candidates else (f"第 {day_number} 天的項目" if day_number is not None else "全部項目")
    if only_unconfirmed:
        scope += "（僅未確認）"
    if not items:
        return ItineraryItemsResult(summary=f"這趟旅程的{scope}是空的。", items=[])
    need_attention = sum(1 for i in items if i.confirm_required and not i.is_confirmed)
    tail = f"，其中 {need_attention} 項必須確認但還沒確認。" if need_attention else "。"
    return ItineraryItemsResult(summary=f"{scope}共 {len(items)} 筆{tail}", items=items)


async def add_itinerary_item(
    client: PostgrestClient,
    trip_id: int,
    name: str,
    day_number: int | None = None,
    start_time: str | None = None,
    duration_minutes: int | None = None,
    category: str | None = None,
    location: str | None = None,
    address: str | None = None,
    booking_ref: str | None = None,
    notes: str | None = None,
    confirm_required: bool = False,
) -> ItineraryItemResult:
    trip = await _get_trip(client, trip_id)
    day = validate_day_number(day_number, trip)
    time = validate_start_time(start_time)

    if day is None and time is not None:
        raise retry_pointless(
            "給了 start_time 卻沒給 day_number——候選項目不該帶時間，會自相矛盾。",
            "要嘛補上 day_number 把它排進某一天，要嘛拿掉 start_time 讓它單純當候選。",
        )

    row = await client.insert(
        ITEMS,
        {
            "trip_id": trip_id,
            "name": name,
            "day_number": day,
            "start_time": time,
            "duration_minutes": duration_minutes,
            "category": category or "other",
            "location": location or "",
            "address": address or "",
            "booking_ref": booking_ref or "",
            "notes": notes or "",
            "confirm_required": confirm_required,
            "is_confirmed": False,
            "source": "mcp",
        },
    )
    item = parse_row(ItineraryItem, [row], "新增的行程項目")
    where = "候選區" if item.day_number is None else f"第 {item.day_number} 天" + (f" {item.start_time}" if item.start_time else "")
    return ItineraryItemResult(
        summary=f"已把「{item.name}」加進旅程「{trip.name}」的{where}。",
        item=item,
    )


async def update_itinerary_item(
    client: PostgrestClient,
    item_id: int,
    name: str | None = None,
    day_number: int | None = None,
    to_candidate: bool = False,
    start_time: str | None = None,
    duration_minutes: int | None = None,
    category: str | None = None,
    location: str | None = None,
    address: str | None = None,
    booking_ref: str | None = None,
    notes: str | None = None,
    confirm_required: bool | None = None,
    is_confirmed: bool | None = None,
) -> ItineraryItemResult:
    if to_candidate and day_number is not None:
        raise retry_pointless(
            "同時要求「退回候選」與「排到第 %s 天」，這兩件事互相矛盾。" % day_number,
            "決定一個：to_candidate=true 是退回候選；給 day_number 是排進某一天。",
        )

    existing_rows = await client.select(ITEMS, {"select": "*", **_where_id(item_id)})
    existing = parse_row(ItineraryItem, existing_rows, f"行程項目（id={item_id}）")

    patch: dict[str, Any] = {}
    if to_candidate:
        # 退回候選就不該留著時間，否則資料自相矛盾（與網頁的 unscheduleItem 一致）
        patch["day_number"] = None
        patch["start_time"] = None
    elif day_number is not None:
        trip = await _get_trip(client, existing.trip_id)
        patch["day_number"] = validate_day_number(day_number, trip)

    if start_time is not None:
        time = validate_start_time(start_time)
        target_day = patch.get("day_number", existing.day_number)
        if target_day is None:
            raise retry_pointless(
                "要設定 start_time，但這個項目還在候選中（沒有 day_number）。",
                "同一次呼叫裡一起給 day_number，把它排進某一天再設時間。",
            )
        patch["start_time"] = time

    optional = {
        "name": name,
        "duration_minutes": duration_minutes,
        "category": category,
        "location": location,
        "address": address,
        "booking_ref": booking_ref,
        "notes": notes,
        "confirm_required": confirm_required,
        "is_confirmed": is_confirmed,
    }
    patch.update({k: v for k, v in optional.items() if v is not None})

    if not patch:
        require_any_field(
            {},
            "update_itinerary_item(item_id=..., day_number=2, start_time='14:00', is_confirmed=true)",
        )

    rows = await client.update(ITEMS, _where_id(item_id), patch)
    item = parse_row(ItineraryItem, rows, f"更新後的行程項目（id={item_id}）")

    changed = []
    if "day_number" in patch:
        changed.append("退回候選" if item.day_number is None else f"排到第 {item.day_number} 天")
    if patch.get("start_time"):
        changed.append(f"時間改為 {item.start_time}")
    if "is_confirmed" in patch:
        changed.append("標記為已確認" if item.is_confirmed else "取消已確認")
    if "name" in patch:
        changed.append("改了名稱")
    other = [k for k in patch if k not in {"day_number", "start_time", "is_confirmed", "name"}]
    if other:
        changed.append("更新了 " + "、".join(other))

    return ItineraryItemResult(
        summary=f"已更新「{item.name}」：{'；'.join(changed) if changed else '無變更'}。",
        item=item,
    )


# ══════════════════════════════════════════════════════════
#  購物
# ══════════════════════════════════════════════════════════
# 注意：這一組連的是「購物」那個 Supabase 專案的 buylist_items 表，
# 不是 supabase_schema.sql 裡的 wishlist——後者是 Streamlit 時代的遺留，
# 現在的購物 Tab 不讀它。詳見 mcp-server/README.md 的「兩個 Supabase 專案」一節。


async def list_wishlist(
    client: PostgrestClient, status: str | None = None
) -> BuylistItemsResult:
    params: dict[str, str] = {"select": "*", "order": "created_at.desc"}
    if status is not None:
        normalised = status.strip().lower()
        if normalised not in {"pending", "purchased"}:
            raise retry_pointless(
                f"status 只接受 'pending'（還沒買）或 'purchased'（已買到），收到的是 {status!r}。",
                "換成這兩個值之一；不給 status 就是全部都列。",
            )
        params["bought"] = "eq.true" if normalised == "purchased" else "eq.false"

    rows = await client.select(BUYLIST, params)
    items = parse_rows(BuylistItem, rows, "購物清單")
    scope = {"pending": "還沒買的", "purchased": "已買到的", None: "全部"}[
        status.strip().lower() if status else None
    ]
    if not items:
        return BuylistItemsResult(summary=f"購物清單裡{scope}項目是空的。", items=[])
    return BuylistItemsResult(
        summary=f"購物清單{scope}共 {len(items)} 筆，例如："
        + "、".join(i.name for i in items[:3])
        + "。",
        items=items,
    )


async def add_wishlist_item(
    client: PostgrestClient,
    username: str,
    name: str,
    price: float | None = None,
    quantity: int | None = None,
    category: str | None = None,
    tag: str | None = None,
    urgency: str | None = None,
    note: str | None = None,
    link: str | None = None,
) -> BuylistItemResult:
    if urgency is not None and urgency not in {"need", "want", "maybe"}:
        raise retry_pointless(
            f"urgency 只接受 'need'（需要）、'want'（想要）、'maybe'（再看看），收到的是 {urgency!r}。",
            "換成這三個值之一，或乾脆不給（預設是 maybe）。",
        )
    row = await client.insert(
        BUYLIST,
        {
            "name": name,
            "price": price if price is not None else 0,
            "quantity": quantity if quantity is not None else 1,
            "category": category or "其他",
            "tag": tag or "",
            "urgency": urgency or "maybe",
            "note": note or "",
            "link": link or "",
            "added_by": username,
            "bought": False,
        },
    )
    item = parse_row(BuylistItem, [row], "新增的購物項目")
    return BuylistItemResult(summary=f"已把「{item.name}」加進購物清單。", item=item)


async def update_wishlist_item(
    client: PostgrestClient,
    item_id: int,
    purchased: bool | None = None,
    name: str | None = None,
    price: float | None = None,
    quantity: int | None = None,
    actual_price: float | None = None,
    category: str | None = None,
    tag: str | None = None,
    urgency: str | None = None,
    note: str | None = None,
    link: str | None = None,
) -> BuylistItemResult:
    patch = require_any_field(
        {
            # 工具面講 purchased，資料表欄位叫 bought，映射在這裡收斂
            "bought": purchased,
            "name": name,
            "price": price,
            "quantity": quantity,
            "actual_price": actual_price,
            "category": category,
            "tag": tag,
            "urgency": urgency,
            "note": note,
            "link": link,
        },
        "update_wishlist_item(item_id=..., purchased=true)",
    )
    rows = await client.update(BUYLIST, _where_id(item_id), patch)
    item = parse_row(BuylistItem, rows, f"更新後的購物項目（id={item_id}）")
    if purchased is True:
        summary = f"已把「{item.name}」標記為買到了。"
    elif purchased is False:
        summary = f"已把「{item.name}」改回還沒買。"
    else:
        summary = f"已更新「{item.name}」的 " + "、".join(patch.keys()) + "。"
    return BuylistItemResult(summary=summary, item=item)
