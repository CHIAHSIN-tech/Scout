"""A5：寫入路徑無法逃出 `trips/`。

規格要求四個被拒案例：`../`、絕對路徑（POSIX 與 Windows 兩種）、
symlink 指向外部、slug 內含路徑分隔字元。

所有寫入都經過 `resolve_trip_path()` 這一個函式，所以打這個函式
就等於打到 service 的每一條寫入路徑——最後一個測試把這件事釘住。
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys

import pytest

from scout_mcp.travel import paths, service
from scout_mcp.travel.paths import TripPathError, resolve_trip_path

GOOD = "2026-09-kr-seoul"


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """把 trips/ 指到 tmp_path，測試絕對不碰真實旅程資料。"""
    monkeypatch.setenv("SCOUT_TRIPS_DIR", str(tmp_path / "trips"))
    (tmp_path / "trips").mkdir()
    return tmp_path


# ── 1. 相對跳脫 ──

@pytest.mark.parametrize("slug", [
    "..", "../..", "../2026-09-kr-seoul", "2026-09-kr-seoul/../..",
])
def test_relative_escape_rejected(slug):
    with pytest.raises(TripPathError):
        resolve_trip_path(slug)


def test_relative_escape_in_filename_rejected():
    with pytest.raises(TripPathError):
        resolve_trip_path(GOOD, "..", "..", "etc")


# ── 2. 絕對路徑 ──

@pytest.mark.parametrize("slug", [
    "/etc/passwd",
    "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "C:/Windows/System32",
    "\\\\server\\share",
])
def test_absolute_path_rejected(slug):
    with pytest.raises(TripPathError):
        resolve_trip_path(slug)


def test_absolute_path_as_filename_rejected():
    for name in ("/etc/passwd", "C:\\Windows\\win.ini"):
        with pytest.raises(TripPathError):
            resolve_trip_path(GOOD, name)


# ── 3. symlink 指向外部 ──

def _link(target, link):
    """建一個會被 resolve() 追出去的連結。

    Windows 上建 symlink 需要開發者模式或管理員權限，但 directory junction 不用，
    而且 `Path.resolve()` 一樣會解開它——對這個測試要驗的東西來說兩者等價。
    """
    try:
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    except OSError:
        if sys.platform != "win32":
            raise
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip(f"這台機器兩種連結都建不出來：{r.stderr.strip()}")
        return "junction"


def test_symlink_pointing_outside_rejected(sandbox):
    outside = sandbox / "outside"
    outside.mkdir()
    kind = _link(outside, sandbox / "trips" / GOOD)
    with pytest.raises(TripPathError) as exc:
        resolve_trip_path(GOOD, "trip.json")
    assert "trips/" in str(exc.value), f"({kind}) 錯誤訊息要說得出問題在哪"


def test_symlink_pointing_inside_is_fine(sandbox):
    real = sandbox / "trips" / "2026-10-jp-osaka"
    real.mkdir()
    _link(real, sandbox / "trips" / GOOD)
    # 解到 trips/ 之內，就算它是連結也沒問題——擋的是逃出去，不是連結本身
    assert resolve_trip_path(GOOD, "trip.json").name == "trip.json"


# ── 4. slug 內含路徑分隔字元 ──

@pytest.mark.parametrize("slug", [
    "2026-09-kr/seoul", "2026-09-kr\\seoul", "2026-09-kr-seoul/sub", "a/b",
])
def test_separator_in_slug_rejected(slug):
    with pytest.raises(TripPathError):
        resolve_trip_path(slug)


@pytest.mark.parametrize("name", ["a/b", "a\\b", "sub/trip.json"])
def test_separator_in_filename_rejected(name):
    with pytest.raises(TripPathError):
        resolve_trip_path(GOOD, name)


# ── 其他守門 ──

def test_slug_must_match_naming_rule():
    for bad in ("seoul", "2026-9-kr-seoul", "2026-09-KR-seoul", "2026-09-kor-seoul", ""):
        with pytest.raises(TripPathError):
            resolve_trip_path(bad)


def test_good_slug_resolves_inside_trips(sandbox):
    p = resolve_trip_path(GOOD, "trip.json")
    assert p == (sandbox / "trips" / GOOD / "trip.json").resolve()


def test_null_byte_rejected():
    with pytest.raises(TripPathError):
        resolve_trip_path(GOOD, "trip\x00.json")


def test_every_write_goes_through_resolve_trip_path():
    """service 裡不得有繞過 resolve_trip_path 的寫入。

    這一條是 A5 真正的保證：上面所有案例都只打一個函式，
    如果 service 有第二條寫入路徑，那些案例就白測了。
    """
    src = inspect.getsource(service)
    # 允許的取得路徑方式：paths.* 底下那幾個 helper
    assert "open(" not in src, "service 不該直接 open()，一律走 paths 的 helper"
    for helper in ("trip_json", "resolve_trip_path", "web_trips_root", "trips_root"):
        assert f"paths.{helper}" in src, f"service 應該透過 paths.{helper}"
    # 不得自己組 Path("trips") 這種相對路徑
    assert 'Path("trips' not in src and "Path('trips" not in src
