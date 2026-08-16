"""離線用的 Supabase PostgREST 替身。

**設計紀律（spec §4 Should）：fake 不得比真 PostgREST 寬鬆。**
具體來說，這個 fake 會在下列情況回 4xx，就像真的 PostgREST 一樣：

  * 對不存在的表操作 → 404
  * 寫入不存在的欄位 → 400（真 PostgREST 回 PGRST204）
  * 送出不支援的 filter 運算子 → 400
  * NOT NULL 欄位缺值 → 400

寬鬆的 fake 會讓測試全綠但正式環境爆炸，那比沒有測試更糟。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlparse

import httpx

# 欄位定義來自 supabase_schema.sql 與 buylist/buylist-schema.sql。
# key = 欄位名, value = (是否必填)
_SCHEMA: dict[str, dict[str, bool]] = {
    "trips": {
        "id": False, "username": True, "name": True, "start_date": True,
        "end_date": True, "notes": False, "created_at": False,
    },
    "itinerary_items": {
        "id": False, "trip_id": True, "day_number": False, "name": True,
        "category": False, "start_time": False, "duration_minutes": False,
        "location": False, "address": False, "booking_ref": False, "notes": False,
        "source": False, "source_id": False, "sort_order": False,
        "confirm_required": False, "is_confirmed": False, "created_at": False,
    },
    "buylist_items": {
        "id": False, "name": True, "price": False, "urgency": False,
        "accessibility": False, "this_month": False, "bought": False,
        "added_by": False, "note": False, "link": False, "category": False,
        "recurring_cost": False, "starred": False, "quantity": False,
        "tag": False, "actual_price": False, "created_at": False,
    },
}

_DEFAULTS: dict[str, dict[str, Any]] = {
    "trips": {"notes": ""},
    "itinerary_items": {
        "category": "other", "duration_minutes": 60, "location": "", "address": "",
        "booking_ref": "", "notes": "", "confirm_required": False,
        "is_confirmed": False, "source": "manual", "sort_order": 0,
    },
    "buylist_items": {
        "price": 0, "urgency": "maybe", "accessibility": "tw_easy", "this_month": True,
        "bought": False, "added_by": "", "note": "", "link": "", "category": "其他",
        "recurring_cost": 0, "starred": False, "quantity": 1, "tag": "",
        "actual_price": None,
    },
}

# 只支援本專案實際會用到的運算子。收到別的就回 400，與真 PostgREST 一致。
_SUPPORTED_OPS = {"eq", "is", "not"}


class FakeSupabase:
    """一個 in-memory 的 PostgREST。用 `as_transport()` 掛到 httpx.AsyncClient。"""

    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            name: [] for name in _SCHEMA
        }
        for name, rows in (tables or {}).items():
            self.tables[name] = [dict(r) for r in rows]
        self._next_id = 1000
        self.calls: list[tuple[str, str]] = []  # (verb, path) 供斷言用

    # ── httpx 掛載 ──

    def as_transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.as_transport())

    # ── 內部 ──

    @staticmethod
    def _json(status: int, payload: Any) -> httpx.Response:
        return httpx.Response(status, json=payload)

    @staticmethod
    def _error(status: int, message: str, code: str = "") -> httpx.Response:
        return httpx.Response(status, json={"message": message, "code": code})

    def _handle(self, request: httpx.Request) -> httpx.Response:
        parsed = urlparse(str(request.url))
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "rest" or parts[1] != "v1":
            return self._error(404, f"no route for {parsed.path}")
        table = parts[2]
        verb = request.method.upper()
        self.calls.append((verb, table))

        if table not in _SCHEMA:
            return self._error(404, f"relation \"public.{table}\" does not exist", "42P01")

        query = parse_qsl(parsed.query, keep_blank_values=True)
        filters = [(k, v) for k, v in query if k not in {"select", "order", "limit"}]

        try:
            rows = self._filter(self.tables[table], filters)
        except ValueError as exc:
            return self._error(400, str(exc), "PGRST100")

        if verb == "GET":
            return self._json(200, rows)

        body = json.loads(request.content or b"null")

        if verb == "POST":
            bad = self._reject_unknown_columns(table, body)
            if bad:
                return bad
            missing = [
                col for col, required in _SCHEMA[table].items()
                if required and body.get(col) is None
            ]
            if missing:
                return self._error(
                    400,
                    f"null value in column \"{missing[0]}\" of relation \"{table}\" "
                    "violates not-null constraint",
                    "23502",
                )
            # 忠實重現 PostgREST：資料列一定含有該表的每一個欄位。
            # 沒送的欄位吃 DB 預設（沒預設就是 NULL）；有送的欄位照送的值，
            # 包含明確送出的 null——那代表「就是要存 NULL」，不會退回預設。
            row: dict[str, Any] = {col: None for col in _SCHEMA[table]}
            row.update(_DEFAULTS.get(table, {}))
            row.update(body)
            row["id"] = self._next_id
            row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self._next_id += 1
            self.tables[table].append(row)
            return self._json(201, [row] if self._wants_representation(request) else [])

        if verb == "PATCH":
            bad = self._reject_unknown_columns(table, body)
            if bad:
                return bad
            for row in rows:
                row.update(body)
            return self._json(200, rows if self._wants_representation(request) else [])

        # 真 PostgREST 對這條路徑上不支援的動詞回 405。
        # 我們的 client 的允許清單會先擋下來，但 fake 仍要如實表現。
        return self._error(405, f"method {verb} not allowed")

    @staticmethod
    def _wants_representation(request: httpx.Request) -> bool:
        return "return=representation" in request.headers.get("Prefer", "")

    def _reject_unknown_columns(self, table: str, body: Any) -> httpx.Response | None:
        if not isinstance(body, dict):
            return self._error(400, "body must be an object", "PGRST102")
        unknown = [k for k in body if k not in _SCHEMA[table]]
        if unknown:
            return self._error(
                400,
                f"Could not find the '{unknown[0]}' column of '{table}' in the schema cache",
                "PGRST204",
            )
        return None

    @staticmethod
    def _coerce(raw: str) -> Any:
        if raw in {"true", "false"}:
            return raw == "true"
        try:
            return int(raw)
        except ValueError:
            return raw

    def _filter(
        self, rows: list[dict[str, Any]], filters: list[tuple[str, str]]
    ) -> list[dict[str, Any]]:
        out = rows
        for column, expr in filters:
            op, _, raw = expr.partition(".")
            if op not in _SUPPORTED_OPS:
                raise ValueError(f'unknown operator "{op}" in filter on column "{column}"')
            if op == "is":
                if raw != "null":
                    raise ValueError(f'"is" only supports null, got "{raw}"')
                out = [r for r in out if r.get(column) is None]
            elif op == "not":
                # 只支援 not.is.null
                if raw != "is.null":
                    raise ValueError(f'unsupported negation "{raw}"')
                out = [r for r in out if r.get(column) is not None]
            else:  # eq
                want = self._coerce(raw)
                out = [r for r in out if self._normalise(r.get(column)) == want]
        return out

    @staticmethod
    def _normalise(value: Any) -> Any:
        # PostgREST 比對時 date 會以字串呈現
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value
