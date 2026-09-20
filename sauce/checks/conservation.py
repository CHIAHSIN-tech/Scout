"""A5：匯入不丟列。每一份匯入檔的每一列都要有去處。

掉列在事後完全看不出來：總表少一百款，跟「市場上就是這麼多」長得一模一樣。
所以這一條驗的不是「數字對得起來」，是**逐筆對得起來**。

兩種檔，兩種驗法：

1. **bulk 的 CSV**（只有 FDC 走這條）：`rows_in == events_written + rejects`。
   這是 spec 寫的那條等式，也是唯一一個「先落地成中間檔、再一次灌進去」的地方。
2. **spool 的 JSONL**：逐行讀回來，確認**每一個 event_id 都在 store 裡**。
   這比算數強：算數只能證明數字湊得起來，逐筆存在證明的是沒有任何一行不見了。
   （spool 的 `events_written` 會小於行數是正常的——同一批事件重跑會產生同樣的 id，
   那些是重複，不是遺失。算數驗法會把重複誤判成掉列，逐筆驗法不會。）
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from evdb.spool import read_spool
from evdb.store import Store

from ..contract import EV_PRODUCT
from . import arg_parser, home_of, report


def _csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def main(argv: list[str] | None = None) -> int:
    ns = arg_parser("python -m sauce.checks.conservation", rules=False).parse_args(argv)
    home = home_of(ns)

    rejects_by_file: dict[str, int] = {}
    for path in sorted(home.rejects.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            name = Path(str(row.get("file") or "")).name
            rejects_by_file[name] = rejects_by_file.get(name, 0) + 1

    with Store(home, read_only=True) as store:
        stored = {r["event_id"] for r in store.rows("SELECT event_id FROM events")}
        # FDC 的帳要逐筆比對，所以順手把庫裡的 fdc 產品編號撈出來（見下面的說明）
        fdc_ids = {str(r["source_record_id"]) for r in store.rows(
            "SELECT source_record_id FROM events WHERE source = 'fdc' "
            "AND event_type = ?", [EV_PRODUCT])}

    problems: list[str] = []
    files: list[dict[str, object]] = []

    # ---- spool：逐筆確認每一個 event_id 都在 store 裡 ----
    for path in sorted(home.spool.rglob("*.jsonl")):
        lines = missing = bad = 0
        for _, ev, err in read_spool(path):
            lines += 1
            if err or ev is None:
                bad += 1
                continue
            if ev.event_id not in stored:
                missing += 1
        files.append({"file": path.name, "kind": "spool", "lines": lines,
                      "missing_from_store": missing, "unparseable": bad})
        if missing:
            problems.append(f"{path.name}：有 {missing} 行的事件不在 store 裡")
        if bad and bad != rejects_by_file.get(path.name, 0):
            problems.append(f"{path.name}：{bad} 行解析失敗，但 rejects 只記了 "
                            f"{rejects_by_file.get(path.name, 0)} 筆")

    # ---- FDC 的帳：帳上記 `event` 的那幾列，每一列都要在庫裡找得到 ----
    #
    # v3 之前 FDC 走 bulk CSV，所以這裡驗的是 `rows_in == spooled + rejects`。
    # v3 把它改走 Spool（payload 裡有巢狀的 nutrients，bulk 的扁平 CSV 裝不下），
    # `candidates.csv` 從此是**帳**而不是輸入：每一列記一個 fdc_id 與它的下場
    # （`event` / `skipped_category` / `skipped_country`）。
    #
    # 所以守恆的說法也換了，而且比原本強：**不是數字對得上，是逐筆對得上**。
    # 帳上說留下來的那 5,032 筆，要一筆一筆在庫裡指得到；
    # 只比總數的話，少了 3 筆又多算 3 筆會剛好抵銷掉。
    repo = Path(home.root).parent
    for path in sorted(repo.glob("state/snapshot-*/*/candidates.csv")):
        outcomes: dict[str, int] = {}
        missing: list[str] = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                outcome = (row.get("outcome") or "").strip()
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                if outcome == "event" and str(row.get("fdc_id") or "") not in fdc_ids:
                    missing.append(str(row.get("fdc_id") or ""))
        files.append({"file": str(path.relative_to(repo)), "kind": "fdc_ledger",
                      "rows_in": sum(outcomes.values()), "outcomes": outcomes,
                      "missing_from_store": len(missing)})
        if missing:
            problems.append(f"{path.name}：帳上記為 event 的 {len(missing)} 筆在庫裡找不到，"
                            f"例如 {missing[:5]}")

    return report("A5 conservation", not problems,
                  {"files": len(files), "rejects_total": sum(rejects_by_file.values()),
                   "detail": files}, problems)


if __name__ == "__main__":
    sys.exit(main())
