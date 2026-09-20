"""子行程一律走 `sauce.proc.run`，不得直接呼叫 subprocess。

## 這條測試在守什麼

Windows 上從非主控台環境啟動主控台程式，**每一個子行程都會彈出一個視窗**。
驗收表有五十幾項、每項一個子行程，其中幾個檢查自己又各開兩三個——
跑一次驗收會在使用者螢幕上彈六十幾次。

**這種失敗在程式這一側完全看不見**：stdout 正常、exit code 正常、
每一個自動化訊號都說「在跑」。它只在有人看著那台機器的時候才看得見，
而那正是它需要一條機械守門員的理由——人眼不是可重複的檢查。

`sauce/proc.py` 是唯一出口，它帶 `CREATE_NO_WINDOW`。
新增的呼叫繞過它就會被這條測試擋下來。

## 為什麼不是「約定好就行」

因為約定沒有 exit code。這件事已經發生過一次（2026-09-20），
而當時所有的測試都是綠的。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: 這兩個檔可以直接用 subprocess：proc.py 是出口本身；
#: 測試檔自己跑子行程是為了驗 CLI 的 exit code，而測試在 CI／終端機裡跑，
#: 不是使用者盯著的桌面。
ALLOWED = {"sauce/proc.py"}

_RAW = re.compile(r"\bsubprocess\.(run|Popen|call|check_output|check_call)\s*\(")


def _sources() -> list[Path]:
    return [p for p in (REPO / "sauce").rglob("*.py")
            if "__pycache__" not in p.parts]


def test_no_direct_subprocess_calls_in_package():
    offenders: list[str] = []
    for path in _sources():
        rel = path.relative_to(REPO).as_posix()
        if rel in ALLOWED:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _RAW.search(line):
                offenders.append(f"{rel}:{n}  {line.strip()}")
    assert not offenders, (
        "這些地方直接呼叫 subprocess，會在 Windows 上彈出主控台視窗。\n"
        "改用 `from .proc import run as proc_run`（或 `..proc`）：\n  "
        + "\n  ".join(offenders))


def test_proc_run_sets_no_window_on_windows():
    """出口本身真的帶了旗標——不然上面那條只是在檢查大家有沒有 import 對的東西。"""
    import sys

    from sauce.proc import NO_WINDOW

    if sys.platform == "win32":
        assert NO_WINDOW == 0x08000000
    else:
        assert NO_WINDOW == 0
