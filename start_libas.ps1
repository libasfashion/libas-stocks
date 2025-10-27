# start_libas.ps1
$Base = "E:\busy-inventory-app"
$Tunnel = "libas-pc1"

# Start Flask app hidden
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd $Base && .\.venv\Scripts\activate && pythonw app.py"

Start-Sleep -Seconds 5

# Start Cloudflare tunnel hidden
Start-Process -WindowStyle Hidden -FilePath "$Base\cloudflared.exe" -ArgumentList "--config $Base\config.yml tunnel run $Tunnel"

Write-Host "✅ LIBAS site is now LIVE!"
