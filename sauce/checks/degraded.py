"""A12：bridge 不吃降級輸出。

把釘住的 model id 換成不存在的字串，抽取必須 exit 非 0，而且**一筆事件都不能寫**。

為什麼這條要單獨驗：prompt 版本是對「某一個模型」驗過的。模型被換掉之後，
同一段 prompt 的輸出品質沒有任何人驗過，但它看起來跟驗過的一模一樣——
所以只能在入口擋，不能事後篩。
"""
from __future__ import annotations

import sys

from evdb.store import Store

from ..proc import run as proc_run
from . import REPO, arg_parser, home_of, report

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
BOGUS = "nvidia/this-model-does-not-exist"


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.degraded", rules=False).parse_args(argv)
    home = home_of(ns)
    with Store(home, read_only=True) as store:
        before = store.count()
    proc = proc_run(
        [PY, "-m", "sauce.extract", "--home", str(home.root), "--what", "reviews",
         "--limit", "5", "--model-id", BOGUS], cwd=REPO)
    with Store(home, read_only=True) as store:
        after = store.count()
    problems = []
    if proc.returncode == 0:
        problems.append("換成不存在的模型之後仍然 exit 0")
    if after != before:
        problems.append(f"寫了 {after - before} 筆事件；降級時應該一筆都不寫")
    return report("A12 degraded", not problems,
                  {"model_id": BOGUS, "exit": proc.returncode,
                   "events_before": before, "events_after": after,
                   "stderr_tail": proc.stderr.strip()[-300:]}, problems)


if __name__ == "__main__":
    sys.exit(main())
