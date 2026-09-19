"""測試共用的假網路層。

`sauce.net.Fetcher` 唯一真正送出請求的地方是可注入的 `opener`，所以測試把那一層換掉，
**其餘規矩照跑**（robots、速率、擋牆、非 2xx 的處理）。這樣測到的是真的那條路徑，
不是另外寫一份模擬。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


class FakeResponse:
    def __init__(self, body: bytes = b"", status: int = 200, url: str = "",
                 headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.status = status
        self.url = url
        self.headers = headers or {}

    def read(self, n: int = -1) -> bytes:
        body, self._body = self._body, b""
        return body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeNet:
    """url → (status, body)。沒登記的網址回 404。每一次呼叫都記下來，測試可以斷言次數。"""

    def __init__(self, routes: dict[str, tuple[int, bytes]] | None = None) -> None:
        self.routes = dict(routes or {})
        self.calls: list[str] = []

    def __call__(self, req, timeout=None, context=None):  # noqa: ANN001
        import urllib.error

        url = req.full_url if hasattr(req, "full_url") else str(req)
        self.calls.append(url)
        status, body = self.routes.get(url, (404, b""))
        if status >= 400:
            raise urllib.error.HTTPError(url, status, "fake", {}, None)
        return FakeResponse(body, status, url)


@pytest.fixture
def fake_net():
    return FakeNet


@pytest.fixture(autouse=True)
def fast_pacing(monkeypatch):
    """測試不需要真的等 1.5 秒。速率邏輯本身另外用單元測試驗。"""
    monkeypatch.setenv("SAUCE_MIN_INTERVAL", "0.2")
