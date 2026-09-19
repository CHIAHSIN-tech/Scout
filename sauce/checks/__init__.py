"""可執行的檢查器。每一支對應驗收表的一條，exit 0 算過、exit 1 算不過。

寫成程式而不是寫成描述，理由很直接：大量產出（幾千列產品、幾千筆評語）沒有人能用眼睛驗，
而「好的輸出長什麼樣」這種描述在事後沒有判定力。同一支檢查器先跑一小批當試樣、
再跑全量當驗收，兩次用的是同一份規則。

每一支都印出**為什麼不過**與不過的樣本，不只印一個數字——
只回報「FAIL」的檢查器等於把除錯工作丟回給人。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from evdb.home import Home
from evdb.store import Store

REPO = Path(__file__).resolve().parent.parent.parent


def view_rows(home: Home, view: str, rules: str) -> list[dict[str, str]]:
    """讀衍生視圖的 rows.csv。沒 derive 過就講清楚，不要當成 0 列。"""
    path = home.views / view.replace(":", "_").replace(".", "_") / rules / "rows.csv"
    if not path.exists():
        raise FileNotFoundError(f"視圖還沒產生：{path}（先跑 evdb derive）")
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def catalog_rows(home: Home, rules: str = "v1") -> list[dict[str, str]]:
    return view_rows(home, "sauce.views:build", rules)


def reviews_rows(home: Home, rules: str = "v1") -> list[dict[str, str]]:
    return view_rows(home, "sauce.views:reviews", rules)


def events(home: Home) -> list[Any]:
    with Store(home, read_only=True) as store:
        return store.all_events()


def report(name: str, ok: bool, detail: dict[str, Any], problems: Iterable[str] = (),
           limit: int = 20) -> int:
    body = {"check": name, "ok": ok, **detail}
    problems = list(problems)
    if problems:
        body["problems_total"] = len(problems)
        body["problems"] = problems[:limit]
    print(json.dumps(body, ensure_ascii=False, indent=1, default=str))
    return 0 if ok else 1


def arg_parser(prog: str, rules: bool = True) -> Any:
    import argparse

    ap = argparse.ArgumentParser(prog=prog)
    ap.add_argument("--home", default=None)
    if rules:
        ap.add_argument("--rules", default="v1")
    return ap


def home_of(ns: Any) -> Home:
    return Home.resolve(getattr(ns, "home", None))
