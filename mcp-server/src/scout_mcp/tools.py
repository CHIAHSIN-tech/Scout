"""把 service 的函式註冊成 MCP 工具。

這一層刻意很薄：**不重複宣告 schema**（那在 contracts.py／service.py 的簽章裡），
只負責綁定 client、寫工具說明、把 ToolError 轉成 agent 看得到的訊息。
"""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

from . import service
from .config import Endpoint, ScoutConfig
from .contracts import (
    BuylistItemResult,
    BuylistItemsResult,
    ItineraryItemResult,
    ItineraryItemsResult,
    TripResult,
    TripsResult,
)
from .rest import PostgrestClient


def register_tools(
    server: MCPServer,
    config: ScoutConfig,
    client_factory: Callable[[Endpoint], PostgrestClient] = PostgrestClient,
) -> None:
    """把工具註冊上去。

    `client_factory` 是給測試用的接縫：整合測試會塞一個接 fake Supabase 的 client
    進來，好在無網路的情況下真的走一次 MCP 協定（spec AC-7）。
    正式執行時用預設值即可。
    """
    itinerary = client_factory(config.itinerary)
    buylist = client_factory(config.buylist)
    who = config.username

    # ── 行程 ──

    @server.tool(
        description="列出所有旅程（名稱、起訖日期）。要操作某趟旅程的項目時，先用這個取得 trip_id。"
    )
    async def list_trips() -> TripsResult:
        return await service.list_trips(itinerary)

    @server.tool(
        description=(
            "列出某趟旅程的行程項目。可以只看某一天（day_number）、"
            "只看還沒排日期的候選（only_candidates）、或只看未確認的（only_unconfirmed）。"
            "day_number 與 only_candidates 不能同時給。"
        )
    )
    async def list_itinerary_items(
        trip_id: int,
        day_number: int | None = None,
        only_candidates: bool = False,
        only_unconfirmed: bool = False,
    ) -> ItineraryItemsResult:
        return (
            await service.list_itinerary_items(
                itinerary, trip_id, day_number, only_candidates, only_unconfirmed
            )
        )

    @server.tool(
        description=(
            "在某趟旅程新增一個行程項目。"
            "不給 day_number 就是「候選」（想去但還沒決定哪天）——這是預設。"
            "start_time 是 'HH:MM' 純文字，且只有在同時給 day_number 時才能用。"
            "confirm_required 表示這件事需不需要訂位／預約。"
        )
    )
    async def add_itinerary_item(
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
        return (
            await service.add_itinerary_item(
                itinerary,
                trip_id,
                name,
                day_number,
                start_time,
                duration_minutes,
                category,
                location,
                address,
                booking_ref,
                notes,
                confirm_required,
            )
        )

    @server.tool(
        description=(
            "修改一個行程項目。用途包含：排進某一天（day_number）、改時間（start_time）、"
            "標記已確認（is_confirmed）、退回候選（to_candidate=true）、改其他欄位。"
            "至少要給一個要改的欄位。注意本 server 不能刪除項目。"
        )
    )
    async def update_itinerary_item(
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
        return (
            await service.update_itinerary_item(
                itinerary,
                item_id,
                name,
                day_number,
                to_candidate,
                start_time,
                duration_minutes,
                category,
                location,
                address,
                booking_ref,
                notes,
                confirm_required,
                is_confirmed,
            )
        )

    @server.tool(
        description="建立一趟新旅程。start_date / end_date 是 'YYYY-MM-DD'，兩者都必填（行程表與時間軸要靠它算天數）。"
    )
    async def create_trip(
        name: str, start_date: str, end_date: str, notes: str | None = None
    ) -> TripResult:
        return (
            await service.create_trip(itinerary, who, name, start_date, end_date, notes)
        )

    # ── 購物 ──
    # 工具名沿用 spec 的 wishlist 用語；實際操作的是購物 Tab 在用的 buylist_items。

    @server.tool(
        description=(
            "列出購物待買清單（Scout 網頁「🛒 購物」Tab 看到的那一份）。"
            "status='pending' 只看還沒買的，'purchased' 只看已買到的，不給就全部列。"
        )
    )
    async def list_wishlist(status: str | None = None) -> BuylistItemsResult:
        return await service.list_wishlist(buylist, status)

    @server.tool(
        description=(
            "加一個想買的東西到購物清單。urgency 可填 'need'（需要）／'want'（想要）／"
            "'maybe'（再看看，預設）。tag 是購物情境，例如「日本」「Costco」。"
        )
    )
    async def add_wishlist_item(
        name: str,
        price: float | None = None,
        quantity: int | None = None,
        category: str | None = None,
        tag: str | None = None,
        urgency: str | None = None,
        note: str | None = None,
        link: str | None = None,
    ) -> BuylistItemResult:
        return (
            await service.add_wishlist_item(
                buylist, who, name, price, quantity, category, tag, urgency, note, link
            )
        )

    @server.tool(
        description=(
            "修改購物清單的某一項。最常用的是 purchased=true（買到了）。"
            "actual_price 是實付金額。至少要給一個要改的欄位。本 server 不能刪除項目。"
        )
    )
    async def update_wishlist_item(
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
        return (
            await service.update_wishlist_item(
                buylist,
                item_id,
                purchased,
                name,
                price,
                quantity,
                actual_price,
                category,
                tag,
                urgency,
                note,
                link,
            )
        )
