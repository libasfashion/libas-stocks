@echo off
cd /d E:\busy-inventory-app
call .\.venv\Scripts\activate.bat
python sync.py >> sync_log.txt 2>&1
