@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem Initialize Git repository with GitHub URL
set "GITHUB_URL=%~1"

if "%GITHUB_URL%"=="" (
    echo Select operation:
    echo 1. Initialize Git repository
    echo 2. Exit
    set /p choice=Enter your choice (1-2): 
    
    if "%choice%"=="1" (
        set /p GITHUB_URL=Enter GitHub URL (e.g., https://github.com/username/repo.git): 
    ) else (
        goto :END
    )
)

echo Initializing Git repository...
git init
if errorlevel 1 (
    echo Error: Failed to initialize repository.
    goto END
)

echo Setting remote origin to %GITHUB_URL%...
git remote add origin %GITHUB_URL%
if errorlevel 1 (
    echo Warning: Failed to add remote origin (might already exist)
    git remote set-url origin %GITHUB_URL%
)

echo Adding all files...
git add .

echo Creating initial commit...
git commit -m "Initial commit"

echo Pushing to master branch...
git push -u origin master

echo Repository initialized and committed to %GITHUB_URL%

:END
pause
endlocal 