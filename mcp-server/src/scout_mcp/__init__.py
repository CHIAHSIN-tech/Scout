"""Scout MCP server — 讓 Claude 直接讀寫 Scout 的行程與購物資料。"""

__all__ = ["build_server", "main"]


def __getattr__(name: str):
    # 延遲載入：只是 import 這個套件不該連帶要求環境變數就緒
    if name in __all__:
        from . import server

        return getattr(server, name)
    raise AttributeError(name)
