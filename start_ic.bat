@echo off
title IC - Standard Autonomous (All-in-One Swarm Platform)
cls
echo ============================================================
echo   ⚡ IC (Standard Autonomous) ALL-IN-ONE SWARM PLATFORM
echo ============================================================
echo.
echo [1/3] Checking Paperclip Swarm Engine (:3100)...
powershell -Command "$client = New-Object System.Net.Sockets.TcpClient; try { $client.Connect('127.0.0.1', 3100); Write-Host '  ✓ Paperclip Engine (:3100) is ALIVE' -ForegroundColor Green; $client.Close() } catch { Write-Host '  Starting Paperclip Engine...' -ForegroundColor Yellow; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd C:\Users\JUBER\Downloads\paperclip\server; npx tsx C:\Users\JUBER\.gemini\antigravity-ide\brain\368baf62-d95b-4b24-abaf-30ad5b53d43a\scratch\test_server_run.mjs' -WindowStyle Minimized }"

echo [2/3] Checking React Swarm Studio (:5173)...
powershell -Command "$client = New-Object System.Net.Sockets.TcpClient; try { $client.Connect('127.0.0.1', 5173); Write-Host '  ✓ React Swarm Studio (:5173) is ALIVE' -ForegroundColor Green; $client.Close() } catch { Write-Host '  Starting React UI...' -ForegroundColor Yellow; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd C:\Users\JUBER\Downloads\paperclip\ui; pnpm dev' -WindowStyle Minimized }"

echo [3/3] Launching Unified IC Agency Core (:8000)...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000
