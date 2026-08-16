"""行程工具（spec AC-1 / AC-2 / AC-3 的離線對照）。"""

from __future__ import annotations

import pytest

from scout_mcp import service
from scout_mcp.errors import ToolError

pytestmark = pytest.mark.asyncio


# ── list_trips（AC-1）──


async def test_list_trips_returns_names_and_dates(itinerary_client):
    result = await service.list_trips(itinerary_client)
    assert len(result.trips) == 2
    assert "沖繩四日" in result.summary
    assert "2026-09-01" in result.summary
    assert result.trips[0].total_days == 4


async def test_list_trips_on_empty_database_suggests_next_step(itinerary_client, fake):
    fake.tables["trips"] = []
    result = await service.list_trips(itinerary_client)
    assert result.trips == []
    assert "create_trip" in result.summary


# ── 篩選 ──


async def test_list_items_all(itinerary_client):
    result = await service.list_itinerary_items(itinerary_client, trip_id=1)
    assert len(result.items) == 3
    # 「必須確認但還沒確認」是最該被看見的狀態，摘要要點出來
    assert "1 項必須確認但還沒確認" in result.summary


async def test_list_items_by_day(itinerary_client):
    result = await service.list_itinerary_items(itinerary_client, trip_id=1, day_number=1)
    assert {i.name for i in result.items} == {"美麗海水族館", "國際通燒肉"}


async def test_list_items_only_candidates(itinerary_client):
    result = await service.list_itinerary_items(
        itinerary_client, trip_id=1, only_candidates=True
    )
    assert [i.name for i in result.items] == ["琉球村"]
    assert all(i.day_number is None for i in result.items)


async def test_list_items_only_unconfirmed(itinerary_client):
    result = await service.list_itinerary_items(
        itinerary_client, trip_id=1, only_unconfirmed=True
    )
    assert {i.name for i in result.items} == {"美麗海水族館", "琉球村"}


async def test_day_number_and_only_candidates_conflict_is_caught_locally(
    itinerary_client, fake
):
    with pytest.raises(ToolError) as exc:
        await service.list_itinerary_items(
            itinerary_client, trip_id=1, day_number=2, only_candidates=True
        )
    assert "矛盾" in str(exc.value)
    assert fake.calls == []  # 本地擋下，沒有打後端


# ── add_itinerary_item（AC-2）──


async def test_add_without_day_number_creates_a_candidate(itinerary_client, fake):
    result = await service.add_itinerary_item(
        itinerary_client, trip_id=1, name="第一牧志公設市場"
    )
    assert result.item.day_number is None
    assert "候選區" in result.summary
    stored = [r for r in fake.tables["itinerary_items"] if r["name"] == "第一牧志公設市場"]
    assert len(stored) == 1
    assert stored[0]["day_number"] is None
    assert stored[0]["source"] == "mcp"


async def test_add_with_day_and_time(itinerary_client):
    result = await service.add_itinerary_item(
        itinerary_client, trip_id=1, name="首里城", day_number=2, start_time="09:30"
    )
    assert result.item.day_number == 2
    assert result.item.start_time == "09:30"
    assert "第 2 天 09:30" in result.summary


async def test_time_without_day_is_refused(itinerary_client, fake):
    with pytest.raises(ToolError) as exc:
        await service.add_itinerary_item(
            itinerary_client, trip_id=1, name="X", start_time="09:00"
        )
    assert "自相矛盾" in str(exc.value)
    assert ("POST", "itinerary_items") not in fake.calls


@pytest.mark.parametrize("bad", ["9:00", "25:00", "09:60", "上午九點", "09-00", "0900"])
async def test_bad_time_format_is_caught_locally(itinerary_client, fake, bad):
    with pytest.raises(ToolError) as exc:
        await service.add_itinerary_item(
            itinerary_client, trip_id=1, name="X", day_number=1, start_time=bad
        )
    message = str(exc.value)
    assert "HH:MM" in message
    assert "重試相同參數不會有幫助" in message
    assert ("POST", "itinerary_items") not in fake.calls


@pytest.mark.parametrize("bad_day", [0, 5, 99, -1])
async def test_day_out_of_trip_range_is_caught_locally(itinerary_client, fake, bad_day):
    with pytest.raises(ToolError) as exc:
        await service.add_itinerary_item(
            itinerary_client, trip_id=1, name="X", day_number=bad_day
        )
    message = str(exc.value)
    assert "共 4 天" in message
    assert "旅程第幾天" in message
    assert ("POST", "itinerary_items") not in fake.calls


async def test_unknown_trip_gives_a_prose_error(itinerary_client):
    with pytest.raises(ToolError) as exc:
        await service.add_itinerary_item(itinerary_client, trip_id=999, name="X")
    assert "找不到" in str(exc.value)


# ── update_itinerary_item（AC-3）──


async def test_schedule_a_candidate_and_confirm_it(itinerary_client, fake):
    result = await service.update_itinerary_item(
        itinerary_client, item_id=13, day_number=2, start_time="14:00", is_confirmed=True
    )
    assert result.item.day_number == 2
    assert result.item.start_time == "14:00"
    assert result.item.is_confirmed is True
    assert "排到第 2 天" in result.summary and "已確認" in result.summary

    stored = next(r for r in fake.tables["itinerary_items"] if r["id"] == 13)
    assert (stored["day_number"], stored["start_time"], stored["is_confirmed"]) == (2, "14:00", True)


async def test_to_candidate_clears_the_time_as_well(itinerary_client, fake):
    result = await service.update_itinerary_item(
        itinerary_client, item_id=11, to_candidate=True
    )
    assert result.item.day_number is None
    # 退回候選卻留著時間會自相矛盾
    assert result.item.start_time is None
    assert "退回候選" in result.summary


async def test_to_candidate_with_day_number_is_refused(itinerary_client, fake):
    with pytest.raises(ToolError) as exc:
        await service.update_itinerary_item(
            itinerary_client, item_id=11, to_candidate=True, day_number=2
        )
    assert "矛盾" in str(exc.value)
    assert not any(verb == "PATCH" for verb, _ in fake.calls)


async def test_setting_time_on_a_candidate_without_day_is_refused(itinerary_client):
    with pytest.raises(ToolError) as exc:
        await service.update_itinerary_item(
            itinerary_client, item_id=13, start_time="14:00"
        )
    assert "候選中" in str(exc.value)


async def test_update_with_no_fields_is_refused(itinerary_client, fake):
    with pytest.raises(ToolError) as exc:
        await service.update_itinerary_item(itinerary_client, item_id=11)
    assert "沒有指定任何要修改的欄位" in str(exc.value)
    assert not any(verb == "PATCH" for verb, _ in fake.calls)


async def test_update_day_is_validated_against_the_items_own_trip(itinerary_client):
    with pytest.raises(ToolError) as exc:
        await service.update_itinerary_item(itinerary_client, item_id=11, day_number=9)
    assert "共 4 天" in str(exc.value)


# ── create_trip（Should）──


async def test_create_trip(itinerary_client, fake):
    result = await service.create_trip(
        itinerary_client, "stanley", "台南吃飯", "2026-12-01", "2026-12-03"
    )
    assert result.trip.total_days == 3
    assert "共 3 天" in result.summary
    assert any(r["name"] == "台南吃飯" for r in fake.tables["trips"])


async def test_create_trip_rejects_reversed_dates(itinerary_client, fake):
    with pytest.raises(ToolError) as exc:
        await service.create_trip(
            itinerary_client, "stanley", "壞資料", "2026-12-05", "2026-12-01"
        )
    assert "早於" in str(exc.value)
    assert not any(verb == "POST" for verb, _ in fake.calls)
