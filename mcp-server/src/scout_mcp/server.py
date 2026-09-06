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


def _use_system_certificates() -> None:
    """讓 TLS 驗證改用作業系統的憑證庫，而不是 certifi 內建的那份。

    為什麼需要：企業網路／防毒軟體常會做 TLS 中間人,簽發的根憑證只裝在
    作業系統憑證庫裡,certifi 那份固定清單沒有它。結果就是連 Supabase 會
    直接 CERTIFICATE_VERIFY_FAILED,而瀏覽器與其他程式都好好的。

    這不是只為某一台機器打的補丁——走 OS 憑證庫本來就比較正確,
    Windows 讀憑證存放區、macOS 讀 Keychain,兩邊都尊重使用者自己的信任設定。

    失敗路徑：truststore 有問題時不讓 server 起不來,退回 certifi 預設行為,
    只在 stderr 留一行說明(stdout 屬於 JSON-RPC,不能碰)。
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception as exc:  # noqa: BLE001 — 任何失敗都只降級,不中斷啟動
        print(
            f"Scout MCP server：無法啟用系統憑證庫({exc})，改用 certifi 預設清單。"
            "若接著出現 CERTIFICATE_VERIFY_FAILED，原因就在這裡。",
            file=sys.stderr,
        )


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
    _use_system_certificates()   # 必須早於任何 HTTPS 連線
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
