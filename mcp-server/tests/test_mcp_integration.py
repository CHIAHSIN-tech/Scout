"""真的走一次 MCP 協定，不是只呼叫 service 函式。

驗的是 service 測試看不到的那一層：工具有沒有註冊上去、參數 schema 對不對、
回傳有沒有變成 structured content、ToolError 有沒有變成 agent 看得到的錯誤。
全程無網路——client 接的是 fake Supabase（spec AC-7）。

這是 AC-1 ~ AC-4 在離線環境下能做到的最接近的驗證。**真正的 AC-1 ~ AC-4 需要
在 Claude Code 裡對真實 Supabase 跑過一次**，見 mcp-server/README.md 的驗收章節。
"""

from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolRequestParams

from scout_mcp.config import Endpoint, ScoutConfig
from scout_mcp.instructions import SERVER_INSTRUCTIONS
from scout_mcp.rest import PostgrestClient
from scout_mcp.tools import register_tools

pytestmark = pytest.mark.asyncio


@pytest.fixture
def server(fake) -> MCPServer:
    config = ScoutConfig(
        itinerary=Endpoint(url="https://a.supabase.co", key="ka", label="行程"),
        buylist=Endpoint(url="https://b.supabase.co", key="kb", label="購物"),
        username="stanley",
    )
    srv = MCPServer(name="scout", instructions=SERVER_INSTRUCTIONS)
    register_tools(srv, config, client_factory=lambda ep: PostgrestClient(ep, client=fake.client()))
    return srv


def payload(result) -> dict:
    """取出工具回傳的 structured payload。"""
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


# ── 註冊面 ──


async def test_all_seven_must_tools_plus_create_trip_are_registered(server):
    names = {t.name for t in await server.list_tools()}
    assert names == {
        "list_trips",
        "list_itinerary_items",
        "add_itinerary_item",
        "update_itinerary_item",
        "list_wishlist",
        "add_wishlist_item",
        "update_wishlist_item",
        "create_trip",
    }


async def test_no_tool_can_remove_anything(server):
    """spec §4 Won't：這版沒有任何刪除工具。"""
    for tool in await server.list_tools():
        assert "delete" not in tool.name.lower()
        assert "remove" not in tool.name.lower()


async def test_instructions_carry_the_three_rules(server):
    text = server.instructions or ""
    assert "沒有刪除能力" in text
    assert "day_number" in text and "旅程第幾天" in text
    assert "候選" in text


async def test_every_tool_returns_summary_plus_structured_payload(server):
    for tool in await server.list_tools():
        schema = tool.output_schema or {}
        props = schema.get("properties", {})
        assert "summary" in props, f"{tool.name} 少了人話摘要"
        assert len(props) >= 2, f"{tool.name} 只有摘要、沒有 structured payload"


# ── 呼叫面：spec §8 的情境，一路走完 ──


async def test_end_to_end_scenario(server, fake):
    # 1) 列旅程（AC-1 的離線對照）
    result = await server.call_tool("list_trips", {})
    data = payload(result)
    assert "沖繩四日" in data["summary"]
    trip_id = data["trips"][0]["id"]

    # 2) 加一個候選（AC-2）
    result = await server.call_tool(
        "add_itinerary_item", {"trip_id": trip_id, "name": "第一牧志公設市場"}
    )
    data = payload(result)
    assert data["item"]["day_number"] is None
    item_id = data["item"]["id"]
    assert "候選區" in data["summary"]

    # 3) 排到第 2 天 14:00 並確認（AC-3）
    result = await server.call_tool(
        "update_itinerary_item",
        {"item_id": item_id, "day_number": 2, "start_time": "14:00", "is_confirmed": True},
    )
    data = payload(result)
    assert (data["item"]["day_number"], data["item"]["start_time"]) == (2, "14:00")
    assert data["item"]["is_confirmed"] is True

    # 資料庫實際狀態（相當於 spec §8 要求的 REST GET 比對）
    stored = next(r for r in fake.tables["itinerary_items"] if r["id"] == item_id)
    assert (stored["day_number"], stored["start_time"], stored["is_confirmed"]) == (2, "14:00", True)

    # 4) 標記已購（AC-4）
    result = await server.call_tool("update_wishlist_item", {"item_id": 21, "purchased": True})
    data = payload(result)
    assert "買到了" in data["summary"]
    assert next(r for r in fake.tables["buylist_items"] if r["id"] == 21)["bought"] is True


async def test_tool_errors_reach_the_agent_as_prose(server):
    """驗 agent 真正會看到的那一層。

    直接呼叫 `call_tool()` 時 SDK 是往上丟例外；轉成 `is_error` 的 CallToolResult
    發生在 `_handle_call_tool`——也就是 agent 實際拿到的東西。散文必須一路活到那裡，
    不能在中途被換成裸狀態碼。
    """
    from mcp.server.mcpserver.exceptions import ToolError as McpToolError

    # (a) 直接呼叫：散文在例外訊息裡
    with pytest.raises(McpToolError) as exc:
        await server.call_tool(
            "add_itinerary_item", {"trip_id": 1, "name": "X", "day_number": 99}
        )
    assert "共 4 天" in str(exc.value)

    # (b) agent 視角：is_error=True，內容是同一段散文
    result = await server._handle_call_tool(
        None,
        CallToolRequestParams(
            name="add_itinerary_item",
            arguments={"trip_id": 1, "name": "X", "day_number": 99},
        ),
    )
    assert result.is_error
    text = "".join(getattr(c, "text", "") for c in result.content)
    assert "共 4 天" in text
    assert "旅程第幾天" in text
    assert "重試相同參數不會有幫助" in text


async def test_missing_required_argument_is_reported(server):
    # SDK 對「參數不符 schema」是直接丟例外（協定層錯誤），不是 is_error 結果
    from mcp.server.mcpserver.exceptions import ToolError as McpToolError

    with pytest.raises(McpToolError) as exc:
        await server.call_tool("add_itinerary_item", {"name": "少了 trip_id"})
    assert "trip_id" in str(exc.value)
