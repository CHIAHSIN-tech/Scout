"""HTTP 動詞允許清單（spec AC-6）。

⚠️ AC-6 的 grep 豁免說明：
   要驗證「移除動詞被拒絕」，測試就必須把那個動詞字面寫出來。
   因此 AC-6 的判定是對 **原始碼** 做的：

       git grep -inE "\"DELETE\"|'DELETE'" -- mcp-server/src/     → 必須為空
       git grep -inE "\"DELETE\"|'DELETE'" -- mcp-server/ ':!mcp-server/tests/'  → 必須為空

   `tests/` 底下的命中只有兩處，都在本檔，且都是「驗證它被拒絕」的斷言。
"""

from __future__ import annotations

import pytest

from scout_mcp.rest import ALLOWED_VERBS, PostgrestClient, VerbNotAllowed
from scout_mcp.config import Endpoint


@pytest.fixture
def client(fake) -> PostgrestClient:
    return PostgrestClient(
        Endpoint(url="https://x.supabase.co", key="k", label="測試"), client=fake.client()
    )


def test_allowlist_is_exactly_three_read_write_verbs():
    assert ALLOWED_VERBS == frozenset({"GET", "POST", "PATCH"})


@pytest.mark.asyncio
@pytest.mark.parametrize("verb", ["DELETE", "PUT", "HEAD", "OPTIONS", "TRACE", "delete"])
async def test_removal_and_other_verbs_are_refused_before_any_request(verb, client, fake):
    with pytest.raises(VerbNotAllowed) as exc:
        await client._request(verb, "trips")

    # 錯誤是散文：說明重試沒用、指向網頁介面
    message = str(exc.value)
    assert "重試不會有幫助" in message
    assert "網頁介面" in message
    # 關鍵：連請求都沒送出去
    assert fake.calls == []


@pytest.mark.asyncio
async def test_the_three_allowed_verbs_do_reach_the_backend(client, fake):
    await client.select("trips", {"select": "*"})
    await client.insert("trips", {
        "username": "t", "name": "測試", "start_date": "2026-01-01", "end_date": "2026-01-02",
    })
    await client.update("trips", {"id": "eq.1"}, {"notes": "改過"})
    assert [verb for verb, _ in fake.calls] == ["GET", "POST", "PATCH"]
