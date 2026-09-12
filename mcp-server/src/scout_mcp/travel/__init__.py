"""旅程頁模組（trip.json → 單檔離線行程表）。

分層刻意與既有的 Supabase 那條線分開：
    schema.py   欄位定義與不變式——**唯一**一份欄位清單，任何地方要驗結構都 import 它
    paths.py    路徑解析與逃逸防護（所有寫入都得經過它）
    service.py  工具背後的實作（建檔、讀寫、建置）
    schedule.py 排程衝突檢查（只回報，永遠不改資料）
    validate.py 命令列驗證器
    page/       渲染器：render(trip: dict) -> str

與既有 8 個 MCP 工具的關係：完全不重疊。那 8 個工具操作 Supabase，
這裡操作本機檔案，兩邊不互相 import、不共用型別。
"""
