"""設定載入。

設定全部走環境變數（12-Factor）：Supabase 的 URL 與 key **絕不寫死在程式碼裡**，
即使它們在前端是公開的 publishable key 也一樣。

缺變數時的行為由 spec AC-5 規定：非零 exit code ＋ stderr 上的人話錯誤，
要指名缺哪個變數、說明該填什麼、給範例值。不可以印一行 KeyError 就結束。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """設定不完整。訊息本身就是要給使用者看的完整說明。"""


@dataclass(frozen=True)
class Endpoint:
    """一個 Supabase 專案的連線資訊。"""

    url: str
    key: str
    label: str  # 出錯時要講得出「是哪一邊」，例如「行程」或「購物」


@dataclass(frozen=True)
class ScoutConfig:
    itinerary: Endpoint  # trips / itinerary_items（珈欣的專案）
    buylist: Endpoint  # buylist_items（Stanley 的專案）
    username: str


# (環境變數名, 說明, 範例值)
_ITINERARY_URL = ("SCOUT_SUPABASE_URL", "行程資料（trips / itinerary_items）的 Supabase 專案網址", "https://xxxxxxxxxxxx.supabase.co")
_ITINERARY_KEY = ("SCOUT_SUPABASE_KEY", "上述專案的 publishable / anon key", "sb_publishable_xxxxxxxxxxxxxxxx")
_BUYLIST_URL = ("SCOUT_BUYLIST_URL", "購物資料（buylist_items）的 Supabase 專案網址", "https://yyyyyyyyyyyy.supabase.co")
_BUYLIST_KEY = ("SCOUT_BUYLIST_KEY", "上述專案的 publishable / anon key", "sb_publishable_yyyyyyyyyyyyyyyy")

_HELP_TAIL = (
    "\n設定方式：在 .mcp.json 的 env 區塊填入，或在啟動 shell 先 export。\n"
    "值可以從 web/config.js（本機設定檔，未進版控）或 Supabase 專案設定頁取得。\n"
    "詳細步驟見 mcp-server/README.md。"
)


def _require(spec: tuple[str, str, str], env: dict[str, str]) -> str:
    name, what, example = spec
    value = (env.get(name) or "").strip()
    if not value:
        raise ConfigError(
            f"缺少環境變數 {name}（{what}）。\n"
            f"請設定後重新啟動，例如：\n"
            f"    {name}={example}"
            f"{_HELP_TAIL}"
        )
    return value


def load_config(env: dict[str, str] | None = None) -> ScoutConfig:
    """從環境變數組出設定。缺任何一個必要變數就丟 ConfigError。

    一次只報第一個缺的變數，訊息完整可照做；不做「一次列出全部缺項」是因為
    使用者照著補完一個再跑，下一個訊息同樣完整，不會更慢，但實作簡單很多。
    """
    env = os.environ if env is None else env
    itinerary = Endpoint(
        url=_require(_ITINERARY_URL, env).rstrip("/"),
        key=_require(_ITINERARY_KEY, env),
        label="行程",
    )
    buylist = Endpoint(
        url=_require(_BUYLIST_URL, env).rstrip("/"),
        key=_require(_BUYLIST_KEY, env),
        label="購物",
    )
    # username 只是紀錄欄位（誰加的），不是權限邊界，所以有預設值、不強制
    username = (env.get("SCOUT_USERNAME") or "").strip() or "stanley"
    return ScoutConfig(itinerary=itinerary, buylist=buylist, username=username)
