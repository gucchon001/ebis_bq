@echo off
setlocal

set "GITHUB_URL=%1"
if "%GITHUB_URL%"=="" (
    set /p "GITHUB_URL=GitHub URL: "
)

echo [LOG] Git init...
git init

echo [LOG] Adding remote...
git remote add origin %GITHUB_URL%

echo [LOG] Adding files...
git add .

echo [LOG] Committing...
git commit -m "Initial commit"

echo [LOG] Pushing to main...
git push -u origin main

echo [DONE] Repository initialized and committed to %GITHUB_URL%
pause
endlocal 