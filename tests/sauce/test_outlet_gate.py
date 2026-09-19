"""A22：白名單是抓取端的擋牆，不是事後的篩子。

A21 是事後稽核，A22 是事前擋牆——**兩條都要，因為事後稽核發現越界時，
東西已經抓回來了。** 所以這裡驗的不是「有沒有記錄」，而是「有沒有送出請求」。
"""
from __future__ import annotations

import csv

import pytest

from sauce import outlets
from sauce.net import Fetcher

WHITELIST_ROWS = [
    {"outlet": "Example Review", "domain": "example.com", "admitted_on": "2026-09-19",
     "admission_basis": "masthead", "evidence_url": "https://example.com/about",
     "tier": "2_editorial", "conflict_of_interest": "none"},
    {"outlet": "Pathy Outlet", "domain": "news.test/food", "admitted_on": "2026-09-19",
     "admission_basis": "methodology_page", "evidence_url": "https://news.test/food/how",
     "tier": "1_methodology", "conflict_of_interest": "none"},
]


@pytest.fixture
def whitelist(tmp_path):
    path = tmp_path / "outlets.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(outlets.COLUMNS), lineterminator="\n")
        w.writeheader()
        w.writerows(WHITELIST_ROWS)
    return outlets.load(path)


def test_admitted_host_passes(whitelist):
    row = outlets.require("https://example.com/best-hot-sauces", whitelist)
    assert row["outlet"] == "Example Review"


def test_www_prefix_is_the_same_host(whitelist):
    assert outlets.admitted("https://www.example.com/x", whitelist)


def test_host_outside_whitelist_raises(whitelist):
    with pytest.raises(outlets.OutletNotAdmitted):
        outlets.require("https://not-on-the-list.test/article", whitelist)


def test_subdomain_does_not_inherit_parent(whitelist):
    """`example.com` 在名單上，不代表 `blog.example.com` 也在。"""
    assert outlets.match("https://blog.example.com/post", whitelist) is None
    with pytest.raises(outlets.OutletNotAdmitted):
        outlets.require("https://blog.example.com/post", whitelist)


def test_path_prefix_selects_the_right_outlet(whitelist):
    assert outlets.match("https://news.test/food/review", whitelist)["outlet"] == "Pathy Outlet"
    assert outlets.match("https://news.test/sport/x", whitelist) is None


def test_fetcher_sends_nothing_for_unlisted_host(tmp_path, monkeypatch, fake_net):
    """擋牆在請求之前：不在名單上時，opener 一次都不該被呼叫。"""
    net = fake_net({})
    monkeypatch.setattr(outlets, "WHITELIST", tmp_path / "outlets.csv")
    fetcher = Fetcher(opener=net)
    fetcher._outlets = []            # 空白名單＝擋掉全部
    with pytest.raises(outlets.OutletNotAdmitted):
        fetcher.get_review("https://example.com/whatever")
    assert net.calls == []
