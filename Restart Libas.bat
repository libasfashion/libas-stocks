@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\busy-inventory-app\stop_libas.ps1"
timeout /t 5 /nobreak >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\busy-inventory-app\start_libas.ps1"
