#!/bin/bash
# BuyList 啟動檔（Mac）：雙擊這個檔即可。
# 第一次雙擊若被擋，到「系統設定 → 隱私權與安全性」按「仍要開啟」一次即可。
# 它會在這個資料夾起一個小伺服器，並用瀏覽器打開買物清單。關掉終端機視窗即停止。
cd "$(dirname "$0")"
( sleep 1; open "http://localhost:8000/" ) &
python3 -m http.server 8000
