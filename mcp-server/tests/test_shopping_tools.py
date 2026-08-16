"""購物工具（spec AC-4 的離線對照）。

工具名沿用 spec 的 wishlist 用語，實際操作的是購物 Tab 在用的 `buylist_items`。
表面用語 purchased ↔ 資料表欄位 bought 的映射也在這裡驗。
"""

from __future__ import annotations

import pytest

from scout_mcp import service
from scout_mcp.errors import ToolError

pytestmark = pytest.mark.asyncio


async def test_list_all(buylist_client):
    result = await service.list_wishlist(buylist_client)
    assert len(result.items) == 2
    assert "全部共 2 筆" in result.summary


async def test_list_pending_only(buylist_client):
    result = await service.list_wishlist(buylist_client, status="pending")
    assert [i.name for i in result.items] == ["登山襪"]
    assert result.items[0].status == "pending"


async def test_list_purchased_only(buylist_client):
    result = await service.list_wishlist(buylist_client, status="purchased")
    assert [i.name for i in result.items] == ["行動電源"]
    assert result.items[0].status == "purchased"


@pytest.mark.parametrize("bad", ["done", "bought", "已買", "PENDING2"])
async def test_bad_status_is_caught_locally(buylist_client, fake, bad):
    with pytest.raises(ToolError) as exc:
        await service.list_wishlist(buylist_client, status=bad)
    assert "'pending'" in str(exc.value)
    assert fake.calls == []


async def test_status_is_case_insensitive(buylist_client):
    result = await service.list_wishlist(buylist_client, status="PURCHASED")
    assert [i.name for i in result.items] == ["行動電源"]


async def test_add_item_records_who_added_it(buylist_client, fake):
    result = await service.add_wishlist_item(
        buylist_client, "chia", "防曬乳", price=350, tag="日本", urgency="need"
    )
    assert result.item.name == "防曬乳"
    assert result.item.status == "pending"
    stored = next(r for r in fake.tables["buylist_items"] if r["name"] == "防曬乳")
    assert stored["added_by"] == "chia"
    assert stored["tag"] == "日本"
    assert stored["bought"] is False


async def test_add_item_defaults(buylist_client, fake):
    await service.add_wishlist_item(buylist_client, "stanley", "隨手記一筆")
    stored = next(r for r in fake.tables["buylist_items"] if r["name"] == "隨手記一筆")
    assert stored["urgency"] == "maybe"
    assert stored["quantity"] == 1
    assert stored["category"] == "其他"


@pytest.mark.parametrize("bad", ["urgent", "high", "需要"])
async def test_bad_urgency_is_caught_locally(buylist_client, fake, bad):
    with pytest.raises(ToolError) as exc:
        await service.add_wishlist_item(buylist_client, "stanley", "X", urgency=bad)
    assert "'need'" in str(exc.value)
    assert fake.calls == []


# ── AC-4：標記已購 ──


async def test_mark_as_purchased_sets_the_bought_column(buylist_client, fake):
    result = await service.update_wishlist_item(buylist_client, item_id=21, purchased=True)
    assert result.item.status == "purchased"
    assert "買到了" in result.summary
    stored = next(r for r in fake.tables["buylist_items"] if r["id"] == 21)
    assert stored["bought"] is True


async def test_unmark_purchased(buylist_client, fake):
    result = await service.update_wishlist_item(buylist_client, item_id=22, purchased=False)
    assert result.item.status == "pending"
    assert "改回還沒買" in result.summary


async def test_update_actual_price(buylist_client, fake):
    result = await service.update_wishlist_item(
        buylist_client, item_id=21, purchased=True, actual_price=420
    )
    assert result.item.actual_price == 420
    stored = next(r for r in fake.tables["buylist_items"] if r["id"] == 21)
    assert stored["actual_price"] == 420


async def test_update_with_no_fields_is_refused(buylist_client, fake):
    with pytest.raises(ToolError) as exc:
        await service.update_wishlist_item(buylist_client, item_id=21)
    assert "沒有指定任何要修改的欄位" in str(exc.value)
    assert fake.calls == []


async def test_unknown_item_gives_prose_error(buylist_client):
    with pytest.raises(ToolError) as exc:
        await service.update_wishlist_item(buylist_client, item_id=999, purchased=True)
    assert "找不到" in str(exc.value)
    assert "list 工具" in str(exc.value)
