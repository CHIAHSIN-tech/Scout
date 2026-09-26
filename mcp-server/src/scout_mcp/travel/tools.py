"""把旅程頁模組註冊成 MCP 工具。

**刻意與 `scout_mcp.tools.register_tools` 分成兩個函式**，不是風格偏好：
既有的整合測試斷言「工具剛好就是那 8 個」，混在一起註冊會讓那個測試變紅（A1 的不回歸）。
分開之後，既有那組的名單原封不動，這裡純粹是增量。

這一層一樣很薄：不重複宣告 schema（那在 service 的簽章與 travel/schema.py 裡），
只負責寫工具說明、把 TravelError／TripPathError 轉成 agent 看得懂的訊息。
"""

from __future__ import annotations

import hashlib
import json
from functools import wraps

from mcp.server.mcpserver import MCPServer

from . import schedule as schedule_mod
from . import service
from .paths import TripPathError
from .service import TravelError


def _friendly(fn):
    """把本模組的例外轉成一句話。agent 看到 traceback 幫不上任何忙。"""
    @wraps(fn)
    async def wrapper(*a, **kw):
        try:
            return await fn(*a, **kw)
        except (TravelError, TripPathError) as exc:
            return {"error": str(exc)}
    return wrapper


def register_travel_tools(server: MCPServer) -> None:
    @server.tool(
        description=(
            "列出本機 trips/ 底下所有旅程，依出發日新到舊，含國家、城市、日期與頁面路徑。"
            "要操作某一趟之前先用這個拿 slug。"
        )
    )
    @_friendly
    async def list_trip_files() -> dict:
        return {"trips": service.list_trip_files()}

    @server.tool(
        description=(
            "建立一趟新旅程的 trip.json 骨架，目錄名是 <YYYY>-<MM>-<國碼兩碼>-<城市>。"
            "country 用 ISO 3166-1 alpha-2（KR／JP／TW…），city 用英文（會轉成 slug）。"
            "已經存在就回傳既有路徑，不覆寫。"
        )
    )
    @_friendly
    async def create_trip_file(
        country: str,
        city: str,
        start_date: str,
        end_date: str,
        title: str | None = None,
        party_size: int | None = None,
        currency: str | None = None,
    ) -> dict:
        return service.create_trip_file(
            country=country, city=city, start_date=start_date, end_date=end_date,
            title=title, party_size=party_size, currency=currency,
        )

    @server.tool(
        description="讀回整份 trip.json。排程討論、要看目前有哪些 place／event 時用這個。"
    )
    @_friendly
    async def read_trip(slug: str) -> dict:
        return service.load(slug)

    @server.tool(
        description=(
            "新增或更新一個地點。place 是物件，至少要有 id 與 name。"
            "hours.sources 是陣列且**追加不覆蓋**——查到第二個來源時兩個都會留著，"
            "建置時會自動把互相矛盾的來源變成一筆待確認，不會替你挑一個。"
            "空的 sources 陣列代表「還沒查證」，頁面上不會印營業時間。"
        )
    )
    @_friendly
    async def upsert_place(slug: str, place: dict) -> dict:
        return service.upsert_place(slug, place)

    @server.tool(
        description=(
            "新增或更新一個行程事件。至少要有 id、day、time、title。"
            "day 是「第幾天」的整數（第 1 天＝1），time 是 'HH:MM' 純文字、目的地當地時間，"
            "不做任何時區換算。locked=true 代表已訂位，求解器與你都不得移動它。"
        )
    )
    @_friendly
    async def upsert_event(slug: str, event: dict) -> dict:
        return service.upsert_event(slug, event)

    @server.tool(
        description=(
            "新增或更新一段交通。from／to 是 places 的 id（或 hotel／airport 這類保留 id）。"
            "往返請存成兩筆，不要合併——合併會讓「去 35 分、回 40 分」只剩一個數字。"
        )
    )
    @_friendly
    async def upsert_leg(slug: str, leg: dict) -> dict:
        return service.upsert_leg(slug, leg)

    @server.tool(
        description=(
            "新增或更新一筆待確認。查不到的事實一律放這裡，不要猜一個值填進行程。"
            "至少要有 id 與 what。"
        )
    )
    @_friendly
    async def upsert_open_question(slug: str, question: dict) -> dict:
        return service.upsert_open_question(slug, question)

    @server.tool(
        description=(
            "寫入子分頁（sections：藥局／天氣／出發前）、車站三語對照表（stations）、"
            "或每天的標題與日落時間（days）。sections 是合併，stations 與 days 是整份取代。"
        )
    )
    @_friendly
    async def set_trip_section(
        slug: str,
        sections: dict | None = None,
        stations: list[dict] | None = None,
        days: list[dict] | None = None,
    ) -> dict:
        return service.set_trip_section(slug, sections=sections, stations=stations, days=days)

    @server.tool(
        description=(
            "檢查排程衝突。**只回報，不會改任何東西。**"
            "moves 是「我打算這樣搬」的清單（[{event_id, to_day, to_time}]），不給就是檢查現況。"
            "每個衝突都會附上「要解掉它得犧牲什麼」的選項清單——取捨由使用者決定，不要自己挑。"
            "查不到資料的項目會出現在 unverified，那是待確認，不是通過。"
        )
    )
    @_friendly
    async def check_schedule(slug: str, moves: list[dict] | None = None) -> dict:
        trip = service.load(slug)
        before = hashlib.sha256(
            json.dumps(trip, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        result = schedule_mod.check_schedule(trip, moves)
        # 這支工具的整個價值建立在「它不會動資料」上，所以順手把證據一起回傳。
        result["trip_sha256"] = before
        return result

    @server.tool(
        description=(
            "建置行程表：產出 trips/<slug>/index.html 與 web/trips/<page_slug>/index.html，"
            "並更新 web/trips/index.json。產出是自含單檔，可以離線開、存到手機。"
            "建置時會自動把「沒查證的營業時間」與「來源打架」寫成待確認。"
        )
    )
    @_friendly
    async def build_trip_page(slug: str) -> dict:
        return service.build_trip_page(slug)
