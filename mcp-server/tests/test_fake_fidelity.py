"""fake Supabase 的忠實度（spec §4 Should：「fake 不得比真 PostgREST 寬鬆」）。

寬鬆的 fake 會讓測試全綠、正式環境爆炸，比沒有測試更糟。
這一組測試釘住 fake 該拒絕的東西——沒有它們，fake 會隨著時間慢慢變成
「任何東西都收」的許願池。
"""

from __future__ import annotations

import pytest

from scout_mcp.config import Endpoint
from scout_mcp.errors import ToolError
from scout_mcp.rest import PostgrestClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client(fake) -> PostgrestClient:
    return PostgrestClient(
        Endpoint(url="https://x.supabase.co", key="k", label="測試"), client=fake.client()
    )


async def test_unknown_table_is_404(client):
    with pytest.raises(ToolError) as exc:
        await client.select("no_such_table", {"select": "*"})
    assert "找不到" in str(exc.value)


async def test_unknown_column_on_insert_is_400(client):
    """真 PostgREST 回 PGRST204；fake 也必須拒絕，不能默默吞掉。"""
    with pytest.raises(ToolError) as exc:
        await client.insert("trips", {
            "username": "t", "name": "X",
            "start_date": "2026-01-01", "end_date": "2026-01-02",
            "colour": "紅色",  # 這個欄位不存在
        })
    assert "看不懂這組參數" in str(exc.value)


async def test_unknown_column_on_update_is_400(client):
    with pytest.raises(ToolError):
        await client.update("trips", {"id": "eq.1"}, {"nonexistent": 1})


async def test_missing_not_null_column_is_400(client):
    with pytest.raises(ToolError):
        await client.insert("trips", {"name": "沒有 username 與日期"})


async def test_unsupported_filter_operator_is_400(client):
    """只實作專案用得到的運算子；沒實作的要明確報錯，不能當成沒有篩選。"""
    with pytest.raises(ToolError):
        await client.select("trips", {"select": "*", "name": "like.*沖繩*"})


async def test_inserted_row_contains_every_column_of_the_table(client, fake):
    """PostgREST 回傳的列一定含有該表的每一個欄位，即使值是 null。"""
    await client.insert("itinerary_items", {"trip_id": 1, "name": "只給必填"})
    row = next(r for r in fake.tables["itinerary_items"] if r["name"] == "只給必填")
    for column in ("day_number", "start_time", "location", "booking_ref", "is_confirmed"):
        assert column in row


async def test_absent_column_falls_back_to_the_table_default(client, fake):
    """沒送 duration_minutes 就該吃資料表預設 60，不是 NULL。"""
    await client.insert("itinerary_items", {"trip_id": 1, "name": "吃預設值"})
    row = next(r for r in fake.tables["itinerary_items"] if r["name"] == "吃預設值")
    assert row["duration_minutes"] == 60
    assert row["category"] == "other"


async def test_explicit_null_beats_the_default(fake):
    """明確送 null 代表「就是要 NULL」，不該被預設值蓋回去。"""
    import httpx

    response = await fake.client().post(
        "https://x.supabase.co/rest/v1/itinerary_items",
        headers={"Prefer": "return=representation"},
        json={"trip_id": 1, "name": "明確 null", "duration_minutes": None},
    )
    assert isinstance(response, httpx.Response)
    assert response.json()[0]["duration_minutes"] is None
