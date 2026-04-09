#!/usr/bin/env pwsh
# Claude Island Setup Script for Windows
# Usage: .\setup.ps1

param(
    [switch]$SkipFrontend,
    [switch]$SkipHooks
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Claude Island Setup for Windows 11" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Please install Python 3.9+ from https://python.org" -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version 2>&1
Write-Host "  Found: $pythonVersion"

# Check uv
Write-Host "[2/5] Checking uv..." -ForegroundColor Yellow
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "  Installing uv..." -ForegroundColor Cyan
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $uvPath = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvPath) {
        Write-Host "  Failed to install uv. Please install manually: https://astral.sh/uv" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  Found uv"

# Setup Python backend with uv
Write-Host "[3/5] Setting up Python backend with uv..." -ForegroundColor Yellow
Set-Location $ProjectRoot\backend
$venvPath = "$ProjectRoot\.venv"

if (Test-Path $venvPath) {
    Write-Host "  Removing existing venv..."
    Remove-Item -Recurse -Force $venvPath
}

Write-Host "  Creating virtual environment..."
uv venv $venvPath

Write-Host "  Installing dependencies..."
uv pip install --python "$venvPath\Scripts\python.exe" -r requirements.txt

Write-Host "  Backend setup complete!"

# Setup Electron frontend
if (-not $SkipFrontend) {
    Write-Host "[4/5] Setting up Electron frontend..." -ForegroundColor Yellow

    # Check Node.js
    $nodePath = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodePath) {
        Write-Host "  Node.js not found. Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Found: $(node --version)"

    Set-Location $ProjectRoot\frontend
    if (Test-Path node_modules) {
        Write-Host "  Removing existing node_modules..."
        Remove-Item -Recurse -Force node_modules
    }

    Write-Host "  Installing npm dependencies..."
    npm install

    Write-Host "  Frontend setup complete!"
}

# Configure Claude Code hooks
if (-not $SkipHooks) {
    Write-Host "[5/5] Configuring Claude Code hooks..." -ForegroundColor Yellow

    # Claude Code settings file location
    $settingsPath = "$env:USERPROFILE\.claude\settings.json"

    # Hooks configuration to add
    $hooksConfig = @{
        hooks = @(
            @{ event = "SessionStart"; url = "http://127.0.0.1:8080/hooks/SessionStart"; async = $true },
            @{ event = "SessionEnd"; url = "http://127.0.0.1:8080/hooks/SessionEnd"; async = $true },
            @{ event = "PreToolUse"; url = "http://127.0.0.1:8080/hooks/PreToolUse"; async = $true },
            @{ event = "PostToolUse"; url = "http://127.0.0.1:8080/hooks/PostToolUse"; async = $true },
            @{ event = "PermissionRequest"; url = "http://127.0.0.1:8080/hooks/PermissionRequest"; async = $true },
            @{ event = "Notification"; url = "http://127.0.0.1:8080/hooks/Notification"; async = $true }
        )
    }

    # Read existing settings or create new
    $settings = @{}
    if (Test-Path $settingsPath) {
        try {
            $existingContent = Get-Content $settingsPath -Raw
            if ($existingContent.Trim()) {
                $settings = $existingContent | ConvertFrom-Json -AsHashtable
            }
        } catch {
            Write-Host "  Warning: Could not read existing settings, starting fresh" -ForegroundColor Yellow
        }
    }

    # Merge hooks (avoid duplicates)
    if ($settings.ContainsKey("hooks")) {
        $existingHooks = $settings.hooks
        $newHookEvents = $hooksConfig.hooks | ForEach-Object { $_.event }
        $filteredExisting = $existingHooks | Where-Object { $_.event -notin $newHookEvents }
        $settings.hooks = @($filteredExisting) + $hooksConfig.hooks
    } else {
        $settings += $hooksConfig
    }

    # Ensure .claude directory exists
    $claudeDir = Split-Path $settingsPath -Parent
    if (-not (Test-Path $claudeDir)) {
        New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
    }

    # Write settings
    $settingsJson = $settings | ConvertTo-Json -Depth 10
    Set-Content -Path $settingsPath -Value $settingsJson -Encoding UTF8

    Write-Host "  Hooks configured at: $settingsPath"
    Write-Host "  Hooks added:"
    $hooksConfig.hooks | ForEach-Object { Write-Host "    - $($_.event): $($_.url)" }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To run Claude Island:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Terminal 1 - Start backend:" -ForegroundColor White
Write-Host "    cd $ProjectRoot\backend" -ForegroundColor Gray
Write-Host "    .\.venv\Scripts\python.exe main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 2 - Start frontend:" -ForegroundColor White
Write-Host "    cd $ProjectRoot\frontend" -ForegroundColor Gray
Write-Host "    npm start" -ForegroundColor Gray
Write-Host ""
Write-Host "Then start Claude Code and the widget will appear on the left side." -ForegroundColor Cyan
Write-Host ""
