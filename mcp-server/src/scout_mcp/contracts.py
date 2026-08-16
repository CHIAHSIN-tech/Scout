"""工具的輸入／輸出契約，單點定義（spec §5 pattern 2）。

註冊工具的地方**不重複宣告** schema——欄位長什麼樣、怎麼驗，只有這一份。
回應一律先過 pydantic；後端多給欄位沒關係（會被忽略），少給必要欄位就是契約不符，
寧可明確報錯，也不要默默回傳半殘資料給 agent（spec §4 Should）。
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import ToolError, retry_pointless

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# ══════════════════════════════════════════════════════════
#  資料模型（對照 supabase_schema.sql 與 buylist/buylist-schema.sql）
# ══════════════════════════════════════════════════════════


class _Row(BaseModel):
    # 後端之後加欄位不該讓這裡整個爆掉，所以允許額外欄位存在但不收進來
    model_config = ConfigDict(extra="ignore")


class Trip(_Row):
    id: int
    name: str
    start_date: date
    end_date: date
    username: str | None = None
    notes: str | None = None

    @property
    def total_days(self) -> int:
        """旅程共幾天（含頭尾）。day_number 的合法範圍就是 1..total_days。"""
        return (self.end_date - self.start_date).days + 1


class ItineraryItem(_Row):
    id: int
    trip_id: int
    name: str
    # day_number 為 None ＝ 候選中（尚未排入某一天），這是 Scout 的核心語意
    day_number: int | None = None
    start_time: str | None = None
    duration_minutes: int | None = None
    category: str | None = None
    location: str | None = None
    address: str | None = None
    booking_ref: str | None = None
    notes: str | None = None
    confirm_required: bool = False
    is_confirmed: bool = False


class BuylistItem(_Row):
    """購物 Tab 的 `buylist_items`。

    注意欄位名稱與 spec 的用語對照：spec 說 `status='purchased'`，
    實際資料表用的是布林 `bought`。工具面沿用 spec 的 purchased 用語，
    到了這一層才映射成 bought，避免 agent 需要知道兩套詞彙。
    """

    id: int
    name: str
    price: float | None = None
    quantity: int | None = None
    bought: bool = False
    urgency: str | None = None
    accessibility: str | None = None
    this_month: bool | None = None
    category: str | None = None
    tag: str | None = None
    note: str | None = None
    link: str | None = None
    added_by: str | None = None
    starred: bool | None = None
    actual_price: float | None = None

    @property
    def status(self) -> str:
        """spec 的用語：pending / purchased。"""
        return "purchased" if self.bought else "pending"


# ══════════════════════════════════════════════════════════
#  工具回應：一句人話摘要 ＋ 完整 structured payload（spec §4 Must）
# ══════════════════════════════════════════════════════════


class TripsResult(BaseModel):
    summary: str = Field(description="給人看的一句話摘要")
    trips: list[Trip]


class ItineraryItemsResult(BaseModel):
    summary: str
    items: list[ItineraryItem]


class ItineraryItemResult(BaseModel):
    summary: str
    item: ItineraryItem


class BuylistItemsResult(BaseModel):
    summary: str
    items: list[BuylistItem]


class BuylistItemResult(BaseModel):
    summary: str
    item: BuylistItem


class TripResult(BaseModel):
    summary: str
    trip: Trip


# ══════════════════════════════════════════════════════════
#  回應驗證
# ══════════════════════════════════════════════════════════


def parse_rows(model: type[BaseModel], rows: list[dict[str, Any]], what: str) -> list[Any]:
    """把 PostgREST 回傳的列轉成模型；不符契約就明確報錯。"""
    try:
        return [model.model_validate(row) for row in rows]
    except ValidationError as exc:
        raise ToolError(
            f"資料庫回傳的{what}不符合預期的欄位結構（contract mismatch）：\n{exc}\n"
            "重試相同參數不會有幫助——這代表資料表結構與本 server 的假設不一致。"
            "下一步：請使用者比對 supabase_schema.sql 與該 Supabase 專案的實際欄位。"
        ) from exc


def parse_row(model: type[BaseModel], rows: list[dict[str, Any]], what: str) -> Any:
    parsed = parse_rows(model, rows, what)
    if not parsed:
        raise ToolError(
            f"找不到符合條件的{what}。\n"
            "重試相同參數不會有幫助。下一步：先用對應的 list 工具確認 id 是否正確、"
            "以及那一列是不是已經被人在網頁上刪掉了。"
        )
    return parsed[0]


# ══════════════════════════════════════════════════════════
#  本地預檢（spec §5 pattern 6）：明顯錯誤在本地擋下，
#  給工具專屬的修正指引，不讓使用者吃 PostgREST 的 generic 4xx
# ══════════════════════════════════════════════════════════


def validate_start_time(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not _TIME_RE.match(text):
        raise retry_pointless(
            f"start_time 必須是 24 小時制的 'HH:MM' 純文字，收到的是 {value!r}。",
            "改成像 '09:00'、'14:30' 這樣的格式再送一次。"
            "注意它不是日期、也不帶時區——Scout 的時間就是目的地當地時間。",
        )
    return text


def validate_day_number(day: int | None, trip: Trip) -> int | None:
    if day is None:
        return None
    if day < 1 or day > trip.total_days:
        raise retry_pointless(
            f"day_number={day} 超出旅程「{trip.name}」的範圍——這趟共 {trip.total_days} 天"
            f"（{trip.start_date} ~ {trip.end_date}），合法值是 1 到 {trip.total_days}。",
            "day_number 指的是「旅程第幾天」而不是日期。"
            "換算成正確的天數再送一次；若想放回候選，改用 to_candidate=true。",
        )
    return day


def require_any_field(fields: dict[str, Any], tool_hint: str) -> dict[str, Any]:
    """update 類工具至少要帶一個可改欄位，否則等於空打一趟。"""
    present = {k: v for k, v in fields.items() if v is not None}
    if not present:
        raise retry_pointless(
            "這次呼叫沒有指定任何要修改的欄位。",
            f"至少帶一個欄位再送一次，例如：{tool_hint}",
        )
    return present
