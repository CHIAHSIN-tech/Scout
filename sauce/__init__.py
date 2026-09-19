"""us-hot-sauce-corpus：在美國買得到的辣醬產品總表，加上掛在它們身上的專業評論語料庫。

這個套件只依賴 evdb（隔壁 repo，可編輯安裝）與標準函式庫。它不 import Scout 的任何
應用程式碼，也不被 Scout 的應用程式碼 import——語料庫的檢索日後可能變成獨立工具，
所以這裡從一開始就不跟 buylist / 行程那邊糾纏（Stanley 2026-09-19）。
"""
__all__ = ["contract", "names", "net", "scores"]
