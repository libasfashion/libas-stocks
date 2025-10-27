# stop_libas.ps1
taskkill /F /IM python.exe /T >$null 2>&1
taskkill /F /IM cloudflared.exe /T >$null 2>&1
Write-Host "🛑 LIBAS Flask and Cloudflare stopped."
