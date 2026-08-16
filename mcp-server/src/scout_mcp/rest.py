"""Supabase PostgREST 的純 HTTP client。

刻意的設計限制（spec §5 pattern 1 與 AC-6）：

  * 這裡**不 import 任何資料庫 driver、不開資料庫連線**。走的是與網頁前端
    完全相同的一條 REST 路（`{SUPABASE_URL}/rest/v1/...`）、同一把 publishable key。
  * 動詞是**正面表列**：只有 GET / POST / PATCH 三個。清單外的動詞在送出前就被擋下，
    連組請求的機會都沒有——這是「本 server 沒有刪除能力」的技術保證，
    不是靠每個工具自律。
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from .config import Endpoint
from .errors import ToolError, describe_http_failure, retry_may_help

# 正面表列。想加動詞必須改這一行，改動會非常顯眼。
ALLOWED_VERBS: frozenset[str] = frozenset({"GET", "POST", "PATCH"})

_TIMEOUT_SECONDS = 20.0


class VerbNotAllowed(ToolError):
    """呼叫端試圖使用允許清單以外的 HTTP 動詞。"""


class PostgrestClient:
    """一個 Supabase 專案的 REST 存取層。"""

    def __init__(self, endpoint: Endpoint, client: httpx.AsyncClient | None = None) -> None:
        self._endpoint = endpoint
        self._client = client  # 測試時注入 fake；正式執行時為 None，臨時建立

    @property
    def label(self) -> str:
        return self._endpoint.label

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._endpoint.key,
            "Authorization": f"Bearer {self._endpoint.key}",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    async def _request(
        self,
        verb: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        prefer: str | None = None,
    ) -> Any:
        if verb not in ALLOWED_VERBS:
            # 這條路徑在正式流程中走不到（沒有工具會送別的動詞），
            # 存在的意義是把「不可能刪除」變成協定層的保證而非慣例。
            raise VerbNotAllowed(
                f"HTTP 動詞 {verb} 不在允許清單內（只允許 "
                f"{', '.join(sorted(ALLOWED_VERBS))}）。\n"
                "重試不會有幫助。本 MCP server 刻意不具備移除資料的能力；"
                "要刪除請到 Scout 網頁介面操作。"
            )

        url = f"{self._endpoint.url}/rest/v1/{table}"
        if params:
            url = f"{url}?{urlencode(params)}"

        headers = self._headers({"Prefer": prefer} if prefer else None)

        try:
            if self._client is not None:
                response = await self._client.request(verb, url, headers=headers, json=json)
            else:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    response = await client.request(verb, url, headers=headers, json=json)
        except httpx.TimeoutException as exc:
            raise retry_may_help(
                f"連線到{self._endpoint.label}資料庫逾時（{_TIMEOUT_SECONDS:.0f} 秒）：{exc}",
                "請使用者確認網路狀態，以及 Supabase 專案有沒有被閒置暫停。",
            ) from exc
        except httpx.HTTPError as exc:
            raise retry_may_help(
                f"連線到{self._endpoint.label}資料庫失敗：{exc}",
                "請使用者確認 MCP 設定裡的 URL 拼寫正確、且電腦可以連上網際網路。",
            ) from exc

        if response.status_code >= 400:
            raise describe_http_failure(
                response.status_code, response.text, table, self._endpoint.label
            )

        if not response.content:
            return []
        try:
            return response.json()
        except ValueError as exc:
            raise retry_may_help(
                f"{self._endpoint.label}資料庫回傳了不是 JSON 的內容："
                f"{response.text[:200]}",
                "若持續發生，請使用者確認 URL 指向的是 Supabase 專案而不是別的網站。",
            ) from exc

    # ── 三個動詞各開一個明確的入口，呼叫端不需要自己傳動詞字串 ──

    async def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        rows = await self._request("GET", table, params=params)
        return rows if isinstance(rows, list) else [rows]

    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        # 值為 None 的欄位整個不送，讓資料表的 DEFAULT 生效
        # （明確送 null 會蓋掉 DEFAULT——例如 duration_minutes 會變成 NULL 而不是 60）。
        # 對可為 NULL 又沒有 DEFAULT 的欄位（day_number / start_time），
        # 不送與送 null 結果相同，都是 NULL＝候選中。
        payload = {k: v for k, v in row.items() if v is not None}
        rows = await self._request(
            "POST", table, json=payload, prefer="return=representation"
        )
        if not rows:
            raise retry_may_help(
                f"寫入 `{table}` 之後，{self._endpoint.label}資料庫沒有回傳新增的那一列。",
                "先用對應的 list 工具確認資料到底有沒有寫進去，再決定要不要重送。",
            )
        return rows[0] if isinstance(rows, list) else rows

    async def update(
        self, table: str, params: dict[str, str], patch: dict[str, Any]
    ) -> list[dict[str, Any]]:
        rows = await self._request(
            "PATCH", table, params=params, json=patch, prefer="return=representation"
        )
        return rows if isinstance(rows, list) else [rows]
