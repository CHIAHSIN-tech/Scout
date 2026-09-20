"""跑子行程的唯一出口。**在 Windows 上不彈視窗。**

## 為什麼要有這個檔

驗收表有五十幾項，每一項都是一個子行程；`idempotent`、`reproducible`、
`degraded` 這幾個檢查自己又各開兩三個。加起來一次驗收會開六十幾個
`python.exe`——而在 Windows 上，從主控台之外的地方啟動主控台程式時，
**每一個都會彈出一個視窗**（`conhost.exe`）。

實際後果是 Stanley 的螢幕在跑驗收的那十幾分鐘裡不停跳視窗，跳到他得
去別的 session 查是誰在彈。那不是「小瑕疵」——它讓這台機器在驗收期間
沒辦法拿來做別的事，而驗收是**半年會跑一次、而且要跑很久**的東西。

## 做法

`CREATE_NO_WINDOW`（0x08000000）。子行程照樣有 stdout／stderr 可以擷取，
只是不配一個看得見的主控台。非 Windows 平台上這個旗標不存在，所以傳 0。

**新增任何 `subprocess` 呼叫都要走這裡。** 直接呼叫 `subprocess.run` 會
再把視窗帶回來，而那種回歸沒有任何測試抓得到——它只在有人看著螢幕時才看得見。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

#: Windows 的 `CREATE_NO_WINDOW`。其他平台沒有這個概念，傳 0。
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def run(command: Sequence[str], *, cwd: Path | str | None = None,
        timeout: int | None = 3600, **kwargs: Any) -> subprocess.CompletedProcess:
    """跑一個子行程並擷取輸出。**不彈視窗**（見模組說明）。"""
    return subprocess.run(
        list(command), cwd=str(cwd) if cwd else None, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
        creationflags=NO_WINDOW, **kwargs)
