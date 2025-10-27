@echo off
cd /d E:\busy-inventory-app
start "" /min .\.venv\Scripts\pythonw.exe app.py
timeout /t 5 >nul
start "" /min cloudflared.exe --config E:\busy-inventory-app\config.yml tunnel run libas-pc1
exit
