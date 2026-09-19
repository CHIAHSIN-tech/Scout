"""抓取層共用的東西：快照目錄、事件的建法、原始內容怎麼落地。

四條抓取工作流（母體／長尾／名單／評論）寫入路徑互不重疊，可以各跑各的；
它們唯一共用的就是這個檔——事件長什麼樣只定義一次，不是每個來源自己發明一套。

## 快照

每次執行有一個 `snapshot_id`。來源抓回來的原始回應寫進
`state/snapshot-<id>/<source>/`，並在 `state/snapshot-<id>/MANIFEST.json` 記下
每個檔的 sha256 與筆數。**快照本身不進版控，MANIFEST 進版控**（Q3）——
半年後重跑時，要分得出「這是新出的辣醬」還是「我們這次抓法不一樣」，靠的是它。
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from evdb.home import Home, now_iso
from evdb.schema import Event, IngestPath, Precision
from evdb.spool import Spool

from . import contract
from .names import gtin14

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "state"


def new_snapshot_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


class Snapshot:
    """一次執行的來源快照。每個來源自己寫自己的子目錄，互不覆蓋。"""

    def __init__(self, snapshot_id: str, root: Path | None = None) -> None:
        self.id = snapshot_id
        self.root = Path(root or STATE) / f"snapshot-{snapshot_id}"
        self.root.mkdir(parents=True, exist_ok=True)

    def dir_for(self, source: str) -> Path:
        d = self.root / source
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write(self, source: str, name: str, data: Any) -> Path:
        """把一份原始回應存下來。dict/list 存成 JSON，其餘原樣寫位元組。"""
        path = self.dir_for(source) / name
        if isinstance(data, (dict, list)):
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        elif isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(bytes(data))
        return path

    def manifest(self, extra: dict[str, Any] | None = None) -> Path:
        """逐檔記 sha256 與大小。這份進版控，快照本體不進。"""
        files = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and p.name != "MANIFEST.json":
                blob = p.read_bytes()
                files.append({"path": p.relative_to(self.root).as_posix(),
                              "bytes": len(blob),
                              "sha256": hashlib.sha256(blob).hexdigest()})
        doc = {"snapshot_id": self.id, "files": len(files), "entries": files}
        if extra:
            for k, v in extra.items():
                doc[k] = v
        path = self.root / "MANIFEST.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
        return path


def spool_events(home: Home, tag: str, events: Iterable[Event]) -> int:
    evs = list(events)
    return Spool(home, tag=tag).write(evs) if evs else 0


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def product_event(*, source: str, key: str, title: str, brand: str = "",
                  url: str | None = None, observed_at: str | None = None,
                  gtin: str = "", payload: dict[str, Any] | None = None,
                  us_availability: str = "unknown") -> Event:
    """一筆目錄型來源記錄。

    名稱**原字保留**：`title` / `brand` 就是來源怎麼寫，這裡不折疊、不清洗。
    折疊是比對層的事（`sauce.names`），抽取層的產出還要回頭跟這份原字比對（A10 第二層）。
    """
    body = {"title": _clean(title), "brand": _clean(brand), "source_key": key,
            "us_availability": us_availability}
    if gtin:
        body["gtin"] = gtin14(gtin) or gtin
    for k, v in (payload or {}).items():
        body[k] = _clean(v)
    return Event(
        entity_type="sauce_observation",
        entity_id=contract.observation_id(source, key),
        event_type=contract.EV_PRODUCT,
        observed_at=observed_at or now_iso(), source=source,
        source_record_id=key, source_url=url,
        ingest_path=IngestPath.BULK.value, payload=body)


def mention_event(*, source: str, key: str, name: str, brand: str = "",
                  url: str | None = None, observed_at: str | None = None,
                  event_time: str | None = None, precision: str = Precision.UNKNOWN.value,
                  payload: dict[str, Any] | None = None) -> Event:
    """一次提及：只有名字，沒有評語。UGC 來源只准產生這一種事件（A20）。"""
    body = {"name": _clean(name), "brand": _clean(brand), "source_key": key,
            "us_availability": "mention_only"}
    for k, v in (payload or {}).items():
        body[k] = _clean(v)
    return Event(
        entity_type="sauce_observation",
        entity_id=contract.observation_id(source, key),
        event_type=contract.EV_MENTION,
        observed_at=observed_at or now_iso(), source=source,
        source_record_id=key, source_url=url,
        event_time=event_time,
        event_time_precision=precision if event_time else Precision.UNKNOWN.value,
        ingest_path=IngestPath.BULK.value, payload=body)


def availability_event(*, source: str, key: str, title: str, url: str,
                       kind: str, observed_at: str | None = None,
                       payload: dict[str, Any] | None = None) -> Event:
    """一次「在美國看得到它在賣」的觀察。`kind` 是 contract.US_AVAILABILITY 的值。"""
    if kind not in contract.US_AVAILABILITY:
        raise ValueError(f"us_availability 不在允許值內：{kind!r}")
    body = {"title": _clean(title), "us_availability": kind, "evidence_url": url,
            "source_key": key}
    for k, v in (payload or {}).items():
        body[k] = _clean(v)
    return Event(
        entity_type="sauce_availability",
        entity_id=contract.observation_id(source, key),
        event_type=contract.EV_AVAILABILITY,
        observed_at=observed_at or now_iso(), source=source,
        source_record_id=key, source_url=url,
        ingest_path=IngestPath.BULK.value, payload=body)


def lineup_event(*, source: str, key: str, season: str, items: list[dict[str, Any]],
                 url: str | None = None, observed_at: str | None = None) -> Event:
    """某一季的選醬名單。名單本身就是產品 metadata（第幾棒、標榜多少 SHU）。"""
    return Event(
        entity_type="sauce_lineup",
        entity_id=contract.observation_id(source, key),
        event_type=contract.EV_LINEUP,
        observed_at=observed_at or now_iso(), source=source,
        source_record_id=key, source_url=url,
        ingest_path=IngestPath.BULK.value,
        payload={"season": season, "items": items, "count": len(items)})
