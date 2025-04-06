@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem Initialize Git repository with URL
set "GITHUB_URL=%~1"
set "COMMAND=git-init"

if "%GITHUB_URL%"=="" (
    echo No GitHub URL provided. What would you like to do?
    echo 1. Initialize a Git repository
    echo 2. Exit
    set /p "CHOICE=Enter your choice (1-2): "
    
    if "%CHOICE%"=="1" (
        set /p "GITHUB_URL=Enter GitHub repository URL: "
    ) else (
        goto END
    )
)

echo [INFO] Initializing Git repository...
git init
if errorlevel 1 (
    echo Error: Failed to initialize repository.
    goto END
)

echo [INFO] Setting remote origin to %GITHUB_URL%...
git remote add origin %GITHUB_URL%
if errorlevel 1 (
    echo Note: Remote origin already exists, updating URL...
    git remote set-url origin %GITHUB_URL%
)

echo [INFO] Adding all files...
git add .

echo [INFO] Creating initial commit...
git commit -m "Initial commit"

echo [INFO] Pushing to master branch...
git push -u origin master
if errorlevel 1 (
    echo Error: Failed to push to master branch.
    goto END
)

echo [DONE] Repository initialized and committed to %GITHUB_URL%

:END
echo.
pause
endlocal 