"""A33：禮貌抓取。robots.txt、每主機速率下限、非 2xx 不產生事件。

這三條在 `sauce/net.py` 裡只實作一次（整個套件只有那個檔能送請求），所以也只要驗一次。
"""
from __future__ import annotations

import time

from sauce.net import Fetcher, _min_interval


def test_robots_disallow_blocks_the_request(fake_net):
    net = fake_net({
        "https://blocked.test/robots.txt": (200, b"User-agent: *\nDisallow: /private\n"),
        "https://blocked.test/private/page": (200, b"secret"),
        "https://blocked.test/public/page": (200, b"ok"),
    })
    fetcher = Fetcher(opener=net)
    denied = fetcher.get("https://blocked.test/private/page")
    assert denied.ok is False
    assert denied.reason == "robots_denied"
    assert "https://blocked.test/private/page" not in net.calls

    allowed = fetcher.get("https://blocked.test/public/page")
    assert allowed.ok is True


def test_missing_robots_means_no_rules(fake_net):
    """讀不到 robots.txt 等於沒有禁止規則——這是協定本身的預設，不是我們放寬。"""
    net = fake_net({"https://open.test/page": (200, b"hello")})
    got = Fetcher(opener=net).get("https://open.test/page")
    assert got.ok and got.body == b"hello"


def test_non_2xx_is_not_usable(fake_net):
    net = fake_net({"https://open.test/robots.txt": (404, b""),
                    "https://open.test/gone": (410, b"")})
    got = Fetcher(opener=net).get("https://open.test/gone", retries=0)
    assert got.ok is False
    assert got.status == 410
    assert got.body == b""          # 呼叫端拿不到任何可以拿來產生事件的東西


def test_rate_limit_spaces_requests_per_host(fake_net, monkeypatch):
    monkeypatch.setenv("SAUCE_MIN_INTERVAL", "0.35")
    net = fake_net({"https://slow.test/robots.txt": (404, b""),
                    "https://slow.test/a": (200, b"a"),
                    "https://slow.test/b": (200, b"b")})
    fetcher = Fetcher(opener=net)
    fetcher.get("https://slow.test/a")
    started = time.monotonic()
    fetcher.get("https://slow.test/b")
    assert time.monotonic() - started >= 0.3


def test_min_interval_cannot_be_disabled(monkeypatch):
    """可以調慢，不可以調到 0。"""
    monkeypatch.setenv("SAUCE_MIN_INTERVAL", "0")
    assert _min_interval() >= 0.2
    monkeypatch.setenv("SAUCE_MIN_INTERVAL", "nonsense")
    assert _min_interval() > 0


def test_retry_only_for_retryable_statuses(fake_net):
    net = fake_net({"https://flaky.test/robots.txt": (404, b""),
                    "https://flaky.test/x": (404, b"")})
    fetcher = Fetcher(opener=net)
    fetcher.get("https://flaky.test/x")
    assert net.calls.count("https://flaky.test/x") == 1      # 404 不重試
