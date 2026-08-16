"""設定與啟動失敗行為（spec AC-5）。"""

from __future__ import annotations

import pytest

from scout_mcp.config import ConfigError, load_config

FULL_ENV = {
    "SCOUT_SUPABASE_URL": "https://a.supabase.co",
    "SCOUT_SUPABASE_KEY": "key-a",
    "SCOUT_BUYLIST_URL": "https://b.supabase.co",
    "SCOUT_BUYLIST_KEY": "key-b",
}


def test_loads_all_four_endpoints():
    config = load_config(FULL_ENV)
    assert config.itinerary.url == "https://a.supabase.co"
    assert config.buylist.key == "key-b"
    assert config.username == "stanley"  # 未設定時的預設


def test_username_is_overridable():
    config = load_config({**FULL_ENV, "SCOUT_USERNAME": "chia"})
    assert config.username == "chia"


def test_trailing_slash_is_stripped():
    config = load_config({**FULL_ENV, "SCOUT_SUPABASE_URL": "https://a.supabase.co/"})
    assert config.itinerary.url == "https://a.supabase.co"


@pytest.mark.parametrize("missing", sorted(FULL_ENV))
def test_missing_variable_names_itself_and_gives_an_example(missing: str):
    env = {k: v for k, v in FULL_ENV.items() if k != missing}
    with pytest.raises(ConfigError) as exc:
        load_config(env)
    message = str(exc.value)
    # AC-5：要指名變數、說明該填什麼、給範例值
    assert missing in message
    assert "supabase.co" in message or "sb_publishable" in message
    assert "README" in message


def test_blank_value_counts_as_missing():
    with pytest.raises(ConfigError):
        load_config({**FULL_ENV, "SCOUT_SUPABASE_URL": "   "})


def test_main_exits_nonzero_and_writes_prose_to_stderr(monkeypatch, capsys):
    """AC-5 的完整路徑：process 以非零 exit code 結束，stderr 有人話。"""
    for name in FULL_ENV:
        monkeypatch.delenv(name, raising=False)

    from scout_mcp.server import main

    code = main()
    captured = capsys.readouterr()

    assert code != 0
    assert captured.out == ""  # stdout 紀律：只屬於 JSON-RPC
    assert "SCOUT_SUPABASE_URL" in captured.err
    assert "無法啟動" in captured.err
