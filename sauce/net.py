"""唯一的對外網路出口。

整個 `sauce/` 套件只有這個檔可以送出 HTTP 請求（A33 用 git grep 驗這件事）。
把它收成一個出口，是為了讓四條規矩只需要實作一次、也只需要驗一次：

1. **robots.txt 說不行就不抓。** 每個主機讀一次、快取起來；不得改 user-agent 繞過。
2. **每個主機有速率下限。** 預設兩次請求之間至少隔 1.5 秒，可用環境變數調慢（不准調快到 0）。
3. **非 2xx 不產生事件。** 呼叫端拿到的是 `ok=False` 的結果，它該做的是跳過，不是猜內容。
4. **評論只抓白名單內的 outlet。** `get_review()` 在**送出請求之前**先查
   `fixtures/sauce/outlets.csv`，不在名單上直接 raise，一個位元組都不抓（A22）。
   事後稽核（A21）發現越界時東西已經抓回來了，所以擋牆一定要在前面。

user-agent 是誠實的：它講明自己是誰、在做什麼。不偽裝瀏覽器、不繞付費牆、不碰需要登入的站。
"""
from __future__ import annotations

import gzip
import os
import threading
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from . import outlets

#: 誠實的識別字串：講明是誰、在做什麼、怎麼聯絡。不偽裝成瀏覽器。
USER_AGENT = ("us-hot-sauce-corpus/1.0 (research corpus of US hot sauces and professional "
              "reviews; contact: stanley.luke.de@gmail.com)")
UA_TOKEN = "us-hot-sauce-corpus"

DEFAULT_MIN_INTERVAL = 1.5      # 秒／每主機
DEFAULT_TIMEOUT = 30
MAX_BYTES = 8 * 1024 * 1024     # 單次回應上限；超過就截斷並標記，不把記憶體吃光

def _ssl_context() -> Any:
    """憑證信任鏈。

    Python 在 Windows 上的預設信任鏈會拒絕一些瀏覽器照收的鏈（實測 query.wikidata.org
    回 "certificate has expired"，curl 與瀏覽器都沒事）。那是信任庫的問題，不是站方的問題，
    而「抓不到」與「站掛了」在事後長得一模一樣，所以這裡把它修掉：
    優先用作業系統的信任庫（`truststore`），沒有就退回 `certifi`，再沒有才用預設。

    **這不是關掉驗證。** 三條路徑都會驗證憑證；差別只在信任哪一份根憑證清單。
    """
    import ssl
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()

RETRIES = 2
RETRYABLE = frozenset({429, 500, 502, 503, 504, 520, 521, 522, 524, 526})
#: 429 的視窗通常是分鐘級，退避就不能是秒級（madb 2026-09-17 那批跑不完的教訓）
RATE_LIMIT_BACKOFF = (30, 90, 180)
OVERLOAD_BACKOFF = (3, 8, 20)
MAX_BACKOFF = 240


class RobotsDenied(Exception):
    """robots.txt 不允許。記進 KNOWN_ISSUES 並跳過該網域，不得改 user-agent 繞過。"""


@dataclass
class Fetch:
    """一次抓取的結果。`ok=False` 的意思是「不要拿它產生任何事件」。"""
    url: str
    status: int | None = None
    body: bytes = b""
    content_type: str = ""
    final_url: str = ""
    ok: bool = False
    reason: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def _min_interval() -> float:
    """可以調慢，不可以調到 0：禮貌抓取的下限寫死在這裡。"""
    try:
        return max(0.2, float(os.environ.get("SAUCE_MIN_INTERVAL", DEFAULT_MIN_INTERVAL)))
    except (TypeError, ValueError):
        return DEFAULT_MIN_INTERVAL


class _HostPacer:
    """每個主機一個節流器。包住每一次真正送出的請求（含重試）。"""

    def __init__(self) -> None:
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            interval = _min_interval()
            gap = time.monotonic() - self._last.get(host, 0.0)
            if gap < interval:
                time.sleep(interval - gap)
            self._last[host] = time.monotonic()


def _retry_after(got: "Fetch") -> float | None:
    """伺服器自己講的等待秒數。它比我們的退避表準，所以優先聽它的。"""
    value = (got.headers or {}).get("retry-after", "")
    try:
        return max(1.0, float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _decode(body: bytes, encoding: str) -> bytes:
    enc = (encoding or "").lower()
    try:
        if "gzip" in enc:
            return gzip.decompress(body)
        if "deflate" in enc:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    except (OSError, zlib.error):
        return body
    return body


class Fetcher:
    """一個抓取工作階段。抓取層各自建一個，不共用全域狀態。"""

    def __init__(self, *, timeout: int = DEFAULT_TIMEOUT, obey_robots: bool = True,
                 user_agent: str = USER_AGENT, opener: Any = None) -> None:
        self.timeout = timeout
        self.obey_robots = obey_robots
        self.user_agent = user_agent
        self.pacer = _HostPacer()
        self._robots: dict[str, RobotFileParser | None] = {}
        self._outlets = outlets.load()
        #: 測試用：換掉真正送出請求的那一層，其餘規矩照跑
        self._opener = opener or urllib.request.urlopen
        self.stats = {"requests": 0, "ok": 0, "non_2xx": 0, "robots_denied": 0,
                      "errors": 0, "retries": 0}

    # ---- robots ----
    def _robots_for(self, host: str, scheme: str) -> RobotFileParser | None:
        if host in self._robots:
            return self._robots[host]
        parser = RobotFileParser()
        parser.set_url(f"{scheme}://{host}/robots.txt")
        try:
            self.pacer.wait(host)
            req = urllib.request.Request(f"{scheme}://{host}/robots.txt",
                                         headers={"User-Agent": self.user_agent})
            with self._opener(req, timeout=self.timeout, context=SSL_CONTEXT) as resp:
                parser.parse(resp.read(MAX_BYTES).decode("utf-8", errors="replace").splitlines())
        except Exception:
            # 讀不到 robots.txt（404、連不上）＝ 沒有禁止規則。這是 robots 協定本身的預設，
            # 不是我們放寬——真的禁止的站會把檔案放出來。
            parser = None
        self._robots[host] = parser
        return parser

    def allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        parts = urlsplit(url)
        parser = self._robots_for(parts.netloc, parts.scheme or "https")
        return True if parser is None else parser.can_fetch(UA_TOKEN, url)

    # ---- 抓取 ----
    def get(self, url: str, *, accept: str = "*/*", retries: int = RETRIES,
            extra_headers: dict[str, str] | None = None) -> Fetch:
        """抓一個公開網址。任何失敗都回 `ok=False` 的結果，不丟例外（呼叫端跳過即可）。

        429 與 5xx 會退避重試。**退避不是禮貌的相反，它就是禮貌**：對方說「太快了」，
        兩秒後再撞一次只是再說一次同樣的話。所以 429 的退避從 30 秒起跳，
        而且伺服器有講 `Retry-After` 就聽它的。
        """
        parts = urlsplit(url)
        host = parts.netloc
        if not host:
            return Fetch(url=url, reason="bad_url")
        if not self.allowed(url):
            self.stats["robots_denied"] += 1
            return Fetch(url=url, reason="robots_denied")

        got = self._get_once(url, accept=accept, extra_headers=extra_headers)
        for attempt in range(retries):
            if got.ok or got.status not in RETRYABLE:
                break
            wait = _retry_after(got) or (RATE_LIMIT_BACKOFF if got.status == 429
                                         else OVERLOAD_BACKOFF)[min(attempt, 2)]
            self.stats["retries"] += 1
            time.sleep(min(wait, MAX_BACKOFF))
            got = self._get_once(url, accept=accept, extra_headers=extra_headers)
        return got

    def _get_once(self, url: str, *, accept: str = "*/*",
                  extra_headers: dict[str, str] | None = None) -> Fetch:
        parts = urlsplit(url)
        host = parts.netloc
        self.pacer.wait(host)
        self.stats["requests"] += 1
        headers_out = {"User-Agent": self.user_agent, "Accept": accept,
                       "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.9"}
        # 額外標頭只給需要憑證的唯讀查詢用（例如 PostgREST 的 apikey）。
        # 憑證永遠從環境或本機設定檔讀，不寫進程式、不進版控。
        for k, v in (extra_headers or {}).items():
            headers_out[k] = v
        req = urllib.request.Request(url, headers=headers_out)
        try:
            with self._opener(req, timeout=self.timeout, context=SSL_CONTEXT) as resp:
                raw = resp.read(MAX_BYTES)
                headers = {k.lower(): v for k, v in dict(getattr(resp, "headers", {}) or {}).items()}
                body = _decode(raw, headers.get("content-encoding", ""))
                status = int(getattr(resp, "status", None) or getattr(resp, "code", 0) or 0)
                ok = 200 <= status < 300
                self.stats["ok" if ok else "non_2xx"] += 1
                return Fetch(url=url, status=status, body=body, ok=ok,
                             content_type=headers.get("content-type", ""),
                             final_url=getattr(resp, "url", url) or url, headers=headers,
                             reason="" if ok else f"status_{status}")
        except urllib.error.HTTPError as exc:
            self.stats["non_2xx"] += 1
            # 429 幾乎都是從這裡出來的，所以標頭要一起帶回去——Retry-After 在裡面。
            headers = {k.lower(): v for k, v in dict(getattr(exc, "headers", {}) or {}).items()}
            return Fetch(url=url, status=int(exc.code), reason=f"status_{exc.code}",
                         headers=headers)
        except Exception as exc:
            self.stats["errors"] += 1
            return Fetch(url=url, reason=f"{type(exc).__name__}: {exc}")

    def download(self, url: str, dest: Any, *, resume: bool = True,
                 chunk: int = 1 << 20) -> dict[str, Any]:
        """把大檔**串流**寫到磁碟，不進記憶體（FDC 的批次檔是好幾百 MB）。

        支援續傳：目的檔已經有一部分時送 `Range`，伺服器回 206 就接著寫。
        伺服器不支援 Range（回 200）就從頭重寫——那是正確行為，不是失敗。
        """
        from pathlib import Path

        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        have = path.stat().st_size if (resume and path.exists()) else 0
        parts = urlsplit(url)
        if not self.allowed(url):
            self.stats["robots_denied"] += 1
            return {"ok": False, "reason": "robots_denied", "bytes": have, "path": str(path)}
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if have:
            headers["Range"] = f"bytes={have}-"
        self.pacer.wait(parts.netloc)
        self.stats["requests"] += 1
        req = urllib.request.Request(url, headers=headers)
        try:
            with self._opener(req, timeout=self.timeout, context=SSL_CONTEXT) as resp:
                status = int(getattr(resp, "status", None) or getattr(resp, "code", 0) or 0)
                mode = "ab" if (status == 206 and have) else "wb"
                if mode == "wb":
                    have = 0
                written = 0
                with open(path, mode) as fh:
                    while True:
                        block = resp.read(chunk)
                        if not block:
                            break
                        fh.write(block)
                        written += len(block)
                self.stats["ok"] += 1
                return {"ok": True, "status": status, "bytes": have + written,
                        "added": written, "path": str(path), "reason": ""}
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and have:        # 已經下載完整了
                self.stats["ok"] += 1
                return {"ok": True, "status": 416, "bytes": have, "added": 0,
                        "path": str(path), "reason": "already_complete"}
            self.stats["non_2xx"] += 1
            return {"ok": False, "status": int(exc.code), "bytes": have, "path": str(path),
                    "reason": f"status_{exc.code}"}
        except Exception as exc:
            self.stats["errors"] += 1
            return {"ok": False, "bytes": have, "path": str(path),
                    "reason": f"{type(exc).__name__}: {exc}"}

    def get_review(self, url: str, *, accept: str = "text/html,*/*") -> tuple[Fetch, dict[str, str]]:
        """抓一篇評論。**先查白名單再送請求**；不在名單上丟 OutletNotAdmitted（A22）。"""
        row = outlets.require(url, self._outlets)
        return self.get(url, accept=accept), row
