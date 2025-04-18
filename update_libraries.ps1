# update_libraries.ps1
# Python Library Update Tool

# Set encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Get the directory where the script is executed
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "===== Python Library Update Tool =====" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python detected: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Error: Python not found." -ForegroundColor Red
    Write-Host "Please make sure Python is installed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating a new one..." -ForegroundColor Yellow
    try {
        python -m venv venv
        Write-Host "Virtual environment created." -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to create virtual environment." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate virtual environment
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated." -ForegroundColor Green
    
    # Set PYTHONPATH to reference project root
    $env:PYTHONPATH = $scriptDir
}
catch {
    Write-Host "Failed to activate virtual environment." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upgrade pip." -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if requirements.txt exists
if (-not (Test-Path "requirements.txt")) {
    Write-Host "requirements.txt not found." -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Press Enter to exit"
    exit 1
}

# Update libraries
Write-Host ""
Write-Host "Updating libraries..." -ForegroundColor Yellow
pip install -r requirements.txt --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to update libraries." -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Currently installed packages:" -ForegroundColor Cyan
pip list
Write-Host ""
Write-Host "Library update completed." -ForegroundColor Green

# Deactivate virtual environment
if (Test-Path Function:\deactivate) {
    deactivate
}

Write-Host ""
Write-Host "Process completed." -ForegroundColor Green
Read-Host "Press Enter to exit"
