#!/usr/bin/env pwsh
# Claude Island Launcher
# Usage: .\start.ps1

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

# Colors for output
function Write-Step { param($msg) Write-Host "[Claude Island] $msg" -ForegroundColor Cyan }
function Write-Err { param($msg) Write-Host "[Error] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Claude Island Launcher" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if .venv exists
$venvPython = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Err "Python environment not found. Please run setup.ps1 first:"
    Write-Host "  .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Start backend
if (-not $FrontendOnly) {
    Write-Step "Starting backend server..."
    Start-Process -FilePath $venvPython -ArgumentList "main.py" -WorkingDirectory "$ProjectRoot\backend" -NoNewWindow -PassThru | ForEach-Object {
        $backendProcess = $_
        Write-Host "  Backend PID: $($backendProcess.Id)" -ForegroundColor Gray

        # Wait a moment for backend to start
        Start-Sleep -Seconds 2

        # Check if backend is running
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "  Backend running on http://127.0.0.1:8080" -ForegroundColor Green
            }
        } catch {
            Write-Warning "Backend may not be responding yet..."
        }
    }
}

# Start frontend
if (-not $BackendOnly) {
    # Check Node.js
    $nodePath = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodePath) {
        Write-Err "Node.js not found. Please install Node.js 18+"
        exit 1
    }

    Write-Step "Starting Electron app..."
    Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory "$ProjectRoot\frontend" -NoNewWindow -PassThru | ForEach-Object {
        $frontendProcess = $_
        Write-Host "  Frontend PID: $($frontendProcess.Id)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Step "Claude Island is starting..."
Write-Host "  - Widget should appear on left side of screen"
Write-Host "  - Start Claude Code to see it in action"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Wait for interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Step "Shutting down..."
    Get-Process | Where-Object { $_.Parent.Id -eq $PID -or $_.Name -in @("python", "electron") } | Stop-Process -Force -ErrorAction SilentlyContinue
}
