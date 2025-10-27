@echo off
cd /d E:\busy-inventory-app
start "" python app.py
timeout /t 5
start "" cloudflared.exe tunnel --url http://127.0.0.1:5000
