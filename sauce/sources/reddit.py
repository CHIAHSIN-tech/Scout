"""Reddit：**只用來發現名字**。

Stanley 2026-09-19 講死的一句話：「I don't care what random people say about a product
at all」。所以這個來源在這個專案裡只回答「這個名字存在嗎」，永遠不回答「它好不好」——
不存留言正文、不存分數、不做情緒分析、不進 `sauce_reviews`。
它產生的唯一事件種類是 `sauce.observation.mention`，A20 會把這件事驗成硬斷言。

存在的理由只有一個：有些新品只有討論區講過，漏掉它在總表上看起來就跟「這款不存在」一樣。

## 憑證

走官方 Data API 的 OAuth。**沒有憑證時回空清單並把節點標成 degraded，不得改用網頁抓取**
（BOUNDS 的外部依賴表）。環境變數：`REDDIT_CLIENT_ID`、`REDDIT_CLIENT_SECRET`。
兩個都沒設就直接回傳 degraded，連一個請求都不送。
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from evdb.schema import Event

from .. import harvest
from ..net import Fetcher

SOURCE = "reddit"
OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"

SUBREDDITS = ("hotsauce", "spicy", "chilepeppers", "HotPeppers")
QUERIES = ("new sauce", "just tried", "recommendation", "favorite hot sauce")


def credentials() -> tuple[str, str]:
    return (os.environ.get("REDDIT_CLIENT_ID", "").strip(),
            os.environ.get("REDDIT_CLIENT_SECRET", "").strip())


def configured() -> bool:
    cid, secret = credentials()
    return bool(cid and secret)


def fetch(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
          log: Any = None) -> dict[str, Any]:
    """沒有憑證就 degraded。有憑證的路徑在這裡是個介面樁，不偽造任何資料。"""
    if not configured():
        if log:
            print("  reddit SKIP 沒有 REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET，標 degraded",
                  file=log, flush=True)
        return {"source": SOURCE, "events": [], "kept": 0, "status": "degraded",
                "reason": "no_credentials"}
    # 有憑證時要做的事：拿 token → 逐個 subreddit 搜尋 → 只取標題裡的品名 →
    # 產生 mention 事件。留言正文、分數、情緒一律不取（見模組說明）。
    return {"source": SOURCE, "events": [], "kept": 0, "status": "degraded",
            "reason": "not_implemented_credentials_present"}


def harvest_all(fetcher: Fetcher, snapshot: harvest.Snapshot, observed_at: str,
                log: Any = None) -> dict[str, Any]:
    return fetch(fetcher, snapshot, observed_at, log)
