"""進入點。

stdout 紀律（spec §5 pattern 5）：stdout 只屬於 JSON-RPC。
所有診斷訊息一律走 stderr——這個檔案裡不會有任何 print() 到 stdout。
"""

from __future__ import annotations

import sys

from mcp.server.mcpserver import MCPServer

from .config import ConfigError, load_config
from .instructions import SERVER_INSTRUCTIONS
from .tools import register_tools


def build_server() -> MCPServer:
    """組出設定好的 server。設定不完整時丟 ConfigError。"""
    config = load_config()
    server = MCPServer(
        name="scout",
        title="Scout 旅程與購物",
        instructions=SERVER_INSTRUCTIONS,
        version="0.1.0",
    )
    register_tools(server, config)
    return server


def main() -> int:
    try:
        server = build_server()
    except ConfigError as exc:
        # AC-5：非零 exit code ＋ stderr 上指名變數、說明該填什麼、給範例的人話錯誤
        print(f"Scout MCP server 無法啟動。\n\n{exc}", file=sys.stderr)
        return 1

    server.run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
