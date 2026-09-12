"""旅程檔案的路徑解析——**所有寫入都必須經過 resolve_trip_path()**。

為什麼只留一個入口：路徑逃逸是那種「每個呼叫點各自檢查一次，總有一個漏掉」的問題。
把檢查集中在一個函式，測試只要打這一個函式，就等於打到所有寫入路徑（規格 A5）。

四種被擋掉的情況（tests/test_travel_paths.py 各有案例）：
    1. 相對跳脫      "../../etc"
    2. 絕對路徑      "/etc/passwd"、"C:\\Windows\\System32"
    3. symlink 指向外部
    4. slug 裡夾路徑分隔字元   "a/b"、"a\\b"

本模組**不建立、不刪除任何東西**，只回傳一個確定安全的 Path。
"""

from __future__ import annotations

import os
from pathlib import Path

from .schema import DIR_NAME_RE


class TripPathError(ValueError):
    """路徑不合法。訊息是給 agent 與使用者看的繁體中文。"""


def trips_root() -> Path:
    """`trips/` 的絕對路徑。

    預設由本檔位置往上推到 repo 根目錄；測試與其他機器可用環境變數
    `SCOUT_TRIPS_DIR` 覆蓋（測試靠它寫進 tmp_path，不碰真實旅程資料）。
    """
    override = os.environ.get("SCOUT_TRIPS_DIR")
    if override:
        return Path(override).resolve()
    # travel/ → scout_mcp/ → src/ → mcp-server/ → repo 根目錄
    return (Path(__file__).resolve().parents[4] / "trips").resolve()


def _reject_segment(seg: str, what: str) -> None:
    if not seg:
        raise TripPathError(f"{what} 不能是空字串")
    if seg in (".", ".."):
        raise TripPathError(f"{what} 不能是 {seg!r}")
    if "/" in seg or "\\" in seg:
        raise TripPathError(f"{what} 不能含路徑分隔字元：{seg!r}")
    if os.path.isabs(seg) or (len(seg) >= 2 and seg[1] == ":"):
        raise TripPathError(f"{what} 不能是絕對路徑：{seg!r}")
    if "\x00" in seg:
        raise TripPathError(f"{what} 含 NUL 字元")


def resolve_trip_path(slug: str, *parts: str) -> Path:
    """回傳 `trips/<slug>/<parts...>` 的絕對路徑，確定在 `trips/` 之內。

    `slug` 必須符合目錄命名規則（`<YYYY>-<MM>-<cc>-<city>`）；`parts` 是檔名，
    每一段都不得含分隔字元。不合法一律丟 TripPathError，**不回傳「修正後」的路徑**
    ——默默修正會讓呼叫端以為自己寫對了。
    """
    if not isinstance(slug, str):
        raise TripPathError(f"slug 必須是字串，收到 {type(slug).__name__}")
    _reject_segment(slug, "slug")
    if not DIR_NAME_RE.match(slug):
        raise TripPathError(
            f"slug 不符合 <YYYY>-<MM>-<國碼兩碼>-<城市>：{slug!r}"
        )
    for p in parts:
        if not isinstance(p, str):
            raise TripPathError(f"路徑片段必須是字串，收到 {type(p).__name__}")
        _reject_segment(p, "路徑片段")

    root = trips_root()
    candidate = root.joinpath(slug, *parts)
    # resolve() 會把途中的 symlink 一併解開——第 3 種逃脫（symlink 指向外部）
    # 就是靠這一步變成「解完不在 root 底下」而被擋住。
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise TripPathError(
            f"路徑解出來不在 trips/ 之內（可能是 symlink 指向外部）：{resolved}"
        )
    return resolved


def trip_dir(slug: str) -> Path:
    """某趟旅程的資料夾。"""
    return resolve_trip_path(slug)


def trip_json(slug: str) -> Path:
    """某趟旅程的 trip.json。"""
    return resolve_trip_path(slug, "trip.json")


def web_trips_root() -> Path:
    """部署用的 `web/trips/`。

    與 `trips/` 分開：前者是資料（單一事實來源），後者是建置產物。
    這裡不做逃逸檢查，因為寫進去的檔名一律是 `page_slug`，而 page_slug 由
    schema.PAGE_SLUG_RE 管制，不是使用者自由輸入。
    """
    override = os.environ.get("SCOUT_WEB_TRIPS_DIR")
    if override:
        return Path(override).resolve()
    return (Path(__file__).resolve().parents[4] / "web" / "trips").resolve()
