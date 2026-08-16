"""錯誤散文政策。

agent 拿到裸狀態碼（"400 Bad Request"）只能亂猜下一步。所以每個對外錯誤都要回答兩件事：

  (a) 原樣參數重試有沒有用？
  (b) 建議的下一步是什麼？

`ToolError` 的訊息會直接進到 agent 的 context，寫的時候當成在跟人講話。
"""

from __future__ import annotations


class ToolError(Exception):
    """工具失敗。訊息即散文，不需要呼叫端再加工。"""


def retry_pointless(problem: str, next_step: str) -> ToolError:
    """給「參數本身有問題」的失敗——同樣的參數再送一次結果一樣。"""
    return ToolError(f"{problem}\n重試相同參數不會有幫助。下一步：{next_step}")


def retry_may_help(problem: str, next_step: str) -> ToolError:
    """給「暫時性」的失敗——網路、逾時、後端短暫不可用。"""
    return ToolError(
        f"{problem}\n這看起來是暫時性的，原樣重試一次可能就會成功。"
        f"若連續失敗，下一步：{next_step}"
    )


def describe_http_failure(status: int, body: str, table: str, label: str) -> ToolError:
    """把 PostgREST 的回應翻成 agent 用得上的散文。"""
    snippet = body.strip()[:400] or "（後端沒有回傳內容）"

    if status in (401, 403):
        return retry_pointless(
            f"{label}資料庫拒絕了這次存取（HTTP {status}）：{snippet}",
            "這是金鑰或權限問題，不是參數問題。請使用者確認 MCP 設定裡的 key "
            "對應到正確的 Supabase 專案，且該表已對 anon 開放。",
        )
    if status == 404:
        return retry_pointless(
            f"{label}資料庫找不到 `{table}`（HTTP 404）：{snippet}",
            "請確認連的是正確的 Supabase 專案——行程與購物在兩個不同專案，設定容易對調。",
        )
    if status == 409:
        return retry_pointless(
            f"寫入 `{table}` 與現有資料衝突（HTTP 409）：{snippet}",
            "先用對應的 list 工具查目前狀態，確認要改的那一列是否已存在或已被改過。",
        )
    if status == 422 or status == 400:
        return retry_pointless(
            f"{label}資料庫看不懂這組參數（HTTP {status}）：{snippet}",
            "檢查欄位名稱與型別是否符合工具說明；特別是 start_time 必須是 'HH:MM' 純文字、"
            "day_number 是整數的「第幾天」而不是日期。",
        )
    if status >= 500:
        return retry_may_help(
            f"{label}資料庫回報伺服器端錯誤（HTTP {status}）：{snippet}",
            "Supabase 免費方案的專案閒置後會自動暫停，請使用者到 Supabase 後台確認專案是否被 pause。",
        )
    return retry_pointless(
        f"{label}資料庫回傳未預期的狀態 HTTP {status}：{snippet}",
        "先用對應的 list 工具確認目前資料狀態，再決定要不要換一組參數重試。",
    )
