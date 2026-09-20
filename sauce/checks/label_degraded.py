"""A40：視覺節點也不吃降級輸出。

把 `sauce.labelread` 釘住的視覺模型換成不存在的字串，必須 exit 非 0，
而且**一筆事件都不能寫**。

這一條跟 A12（文字抽取的降級閘）是兩條線，不能互相代替：兩邊走的是不同的
prompt 資產、不同的模型、不同的驗證器。文字那條過了，不代表換掉視覺模型時
會被擋下來——而標籤判讀恰恰是**最沒有辦法事後篩**的一層：
轉錄出來的字沒有原文可以比對（原文是一張圖），
一段由沒驗過的模型讀出來的成分表，在庫裡跟驗過的長得一模一樣。
"""
from __future__ import annotations

import sys

from evdb.store import Store

from ..proc import run as proc_run
from . import REPO, arg_parser, home_of, report

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
BOGUS = "meta/this-vision-model-does-not-exist"


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.label_degraded", rules=False).parse_args(argv)
    home = home_of(ns)
    with Store(home, read_only=True) as store:
        before = store.count()
    proc = proc_run(
        [PY, "-m", "sauce.labelread", "--home", str(home.root), "--limit", "3",
         "--model-id", BOGUS], cwd=REPO)
    with Store(home, read_only=True) as store:
        after = store.count()
    problems = []
    if proc.returncode == 0:
        problems.append("換成不存在的視覺模型之後仍然 exit 0")
    if after != before:
        problems.append(f"寫了 {after - before} 筆事件；降級時應該一筆都不寫")
    return report("A40 label_degraded", not problems,
                  {"model_id": BOGUS, "exit": proc.returncode,
                   "events_before": before, "events_after": after,
                   "stderr_tail": proc.stderr.strip()[-300:]}, problems)


if __name__ == "__main__":
    sys.exit(main())
