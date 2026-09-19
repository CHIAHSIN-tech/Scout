"""A7：只追加。第一份快照產生的每一個 event_id 都還在，而且內容沒變。

基準檔由 `--write-baseline` 產生（一行一個 event_id 加內容雜湊）。
半年後用第二份快照重跑之後，再拿同一份基準檔驗：
事件總數只增不減，而且基準裡的每一筆都還在、內容一致。

「內容一致」不需要額外的欄位比對：evdb 的 event_id 就是內容的 SHA-256，
所以 id 還在就代表內容沒變。這一條驗的是**它沒有被刪掉**。
"""
from __future__ import annotations

import sys
from pathlib import Path

from evdb.store import Store

from . import arg_parser, home_of, report


def main(argv: list[str] | None = None) -> int:
    ap = arg_parser("python -m sauce.checks.append_only", rules=False)
    ap.add_argument("--baseline", default=None, help="基準檔（每行一個 event_id）")
    ap.add_argument("--write-baseline", default=None, help="把目前的 event_id 寫成基準檔")
    ns = ap.parse_args(argv)
    home = home_of(ns)
    with Store(home, read_only=True) as store:
        ids = {row["event_id"] for row in store.rows("SELECT event_id FROM events")}

    if ns.write_baseline:
        path = Path(ns.write_baseline)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(ids)) + "\n", encoding="utf-8")
        return report("A7 append_only (baseline written)", True,
                      {"events": len(ids), "baseline": str(path)})

    if not ns.baseline:
        return report("A7 append_only", False, {"events": len(ids)},
                      ["沒有給 --baseline；先用 --write-baseline 產生基準檔"])
    baseline_path = Path(ns.baseline)
    if not baseline_path.exists():
        return report("A7 append_only", False, {"events": len(ids)},
                      [f"基準檔不存在：{baseline_path}"])
    baseline = {ln.strip() for ln in baseline_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()}
    missing = sorted(baseline - ids)
    problems = [f"基準裡的 {len(missing)} 筆事件不見了：{missing[:5]}"] if missing else []
    if len(ids) < len(baseline):
        problems.append(f"事件總數從 {len(baseline)} 掉到 {len(ids)}")
    return report("A7 append_only", not problems,
                  {"baseline_events": len(baseline), "events_now": len(ids),
                   "added": len(ids - baseline), "missing": len(missing)}, problems)


if __name__ == "__main__":
    sys.exit(main())
