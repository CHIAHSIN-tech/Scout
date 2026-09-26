"""附件：訂房確認與機票要內嵌進離線單檔，而且不能把路徑當成入口。

A9 說單檔不連外。附件如果用 <img src="https://…"> 指回 Cloudflare，飛機上就是一個
破圖——所以這裡測的是「圖真的躺在 HTML 裡」，不是「有一個連結指向圖」。

第二條測的是 index.json 被動過手腳時不會變成任意讀檔：pages[] 只認附件資料夾底下的
檔名，寫 `../../trip.json` 讀不出東西。
"""

from __future__ import annotations

import base64
import json

import pytest

from scout_mcp.travel import paths, service
from scout_mcp.travel.page import render

# 1×1 的透明 PNG，內容不重要，重要的是它是二進位、base64 之後認得出來
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def slug(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "trips_root", lambda: tmp_path)
    s = "2026-09-kr-seoul"
    att = tmp_path / s / "attachments"
    att.mkdir(parents=True)
    (att / "a.png").write_bytes(PNG)
    (att / "index.json").write_text(json.dumps([
        {"id": f"{s}/a.png", "label": "Oriens 訂房", "name": "hotel.png",
         "at": "2026-09-19", "pages": ["a.png"]},
    ]), encoding="utf-8")
    return s


def test_圖片內嵌成_data_uri_不是外部連結(slug):
    items = service.load_attachments(slug)
    assert len(items) == 1 and len(items[0]["pages"]) == 1
    html = render({"trip": {"title": "t", "page_slug": "x"}, "attachments": items})
    assert "data:image/png;base64," + base64.b64encode(PNG).decode() in html
    assert "Oriens 訂房" in html
    # 附件不該引進任何外部資源（A9）
    assert "https://" not in html.split('<section class="block" id="attachments"')[1]


def test_沒有附件時不渲染附件區塊(slug, tmp_path):
    (tmp_path / slug / "attachments" / "index.json").unlink()
    assert service.load_attachments(slug) == []
    assert 'id="attachments"' not in render({"trip": {"title": "t", "page_slug": "x"}})


def test_pages_不能指到附件資料夾外面(slug, tmp_path):
    (tmp_path / slug / "trip.json").write_text("{}", encoding="utf-8")
    idx = tmp_path / slug / "attachments" / "index.json"
    idx.write_text(json.dumps([
        {"id": "x", "label": "壞的", "pages": ["../trip.json", "a.png"]},
    ]), encoding="utf-8")
    items = service.load_attachments(slug)
    # 越界的那筆被丟掉，合法的那筆留著
    assert len(items) == 1 and len(items[0]["pages"]) == 1
