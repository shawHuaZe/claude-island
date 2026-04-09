#!/usr/bin/env pwsh
# Claude Island Stop Script
# Usage: .\stop.ps1

Write-Host "Stopping Claude Island..." -ForegroundColor Yellow

# Kill Python processes running main.py
Get-Process | Where-Object {
    $_.CommandLine -like "*main.py*" -or $_.CommandLine -like "*uvicorn*"
} -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Stopping Python process: $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Kill Electron/Node processes
Get-Process | Where-Object {
    $_.Name -eq "electron" -or $_.Name -eq "node" -and $_.CommandLine -like "*electron*"
} -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Stopping Electron process: $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "Claude Island stopped." -ForegroundColor Green
