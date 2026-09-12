"""A2：既有 8 個 MCP 工具的名稱與參數簽章一字未改。

為什麼要凍結成 JSON 快照而不是在測試裡手寫欄位清單：手寫的清單會跟著實作一起被改，
改完測試還是綠的——那就驗不到「沒動到」。快照是**產生於加旅程頁模組之前**的
`tests/fixtures/tool-surface-v1.json`，任何人可以用 git 看它從那天起沒變過。

新工具只允許**增加**條目：這個測試只比對快照裡的 8 個名字，多出來的工具不管。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer

from scout_mcp.config import Endpoint, ScoutConfig
from scout_mcp.rest import PostgrestClient
from scout_mcp.tools import register_tools
from scout_mcp.travel.tools import register_travel_tools

pytestmark = pytest.mark.asyncio

FROZEN = json.loads(
    (Path(__file__).parent / "fixtures" / "tool-surface-v1.json").read_text(encoding="utf-8")
)


def _server(fake) -> MCPServer:
    """跟正式進入點一樣：既有工具 ＋ 旅程頁工具都註冊上去。

    刻意兩個都註冊——只註冊舊的那組，就驗不到「新模組沒有意外蓋掉舊工具」。
    """
    config = ScoutConfig(
        itinerary=Endpoint(url="https://a.supabase.co", key="ka", label="行程"),
        buylist=Endpoint(url="https://b.supabase.co", key="kb", label="購物"),
        username="stanley",
    )
    srv = MCPServer(name="scout")
    register_tools(srv, config, client_factory=lambda ep: PostgrestClient(ep, client=fake.client()))
    register_travel_tools(srv)
    return srv


async def test_frozen_eight_tools_still_exist(fake):
    names = {t.name for t in await _server(fake).list_tools()}
    missing = set(FROZEN) - names
    assert not missing, f"既有工具消失了：{sorted(missing)}"


async def test_frozen_signatures_are_byte_identical(fake):
    tools = {t.name: t for t in await _server(fake).list_tools()}
    for name, frozen in FROZEN.items():
        schema = tools[name].input_schema or {}
        actual = {
            "properties": schema.get("properties", {}),
            "required": sorted(schema.get("required", [])),
        }
        assert actual == frozen, f"{name} 的參數簽章被改了"


async def test_new_tools_are_additive_only(fake):
    """新增是可以的，但不能借機改掉舊的——上面兩個測試已經擋住改；這裡只記錄新增了什麼。"""
    names = {t.name for t in await _server(fake).list_tools()}
    added = names - set(FROZEN)
    # 旅程頁模組預期新增的十個工具，一個不多、一個不少
    assert added == {
        "list_trip_files",
        "create_trip_file",
        "read_trip",
        "upsert_place",
        "upsert_event",
        "upsert_leg",
        "upsert_open_question",
        "set_trip_section",
        "check_schedule",
        "build_trip_page",
    }
