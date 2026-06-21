@echo off
REM BuyList 啟動檔（Windows）：雙擊這個檔即可。
REM 它會在這個資料夾起一個小伺服器，並用瀏覽器打開買物清單。
REM 關掉清單就關掉這個黑視窗即可停止。
cd /d "%~dp0"
start "" http://localhost:8000/
python -m http.server 8000
