@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "GITHUB_URL=%1"
if "%GITHUB_URL%"=="" (
    set /p "GITHUB_URL=Enter GitHub URL: "
)

echo [INFO] Initializing Git repository...
git init

echo [INFO] Setting remote origin to %GITHUB_URL%...
git remote add origin %GITHUB_URL%

echo [INFO] Adding all files...
git add .

echo [INFO] Creating initial commit...
git commit -m "Initial commit"

echo [INFO] Pushing to main branch...
git push -u origin main

echo [DONE] Repository initialized and committed to %GITHUB_URL%
pause
endlocal 