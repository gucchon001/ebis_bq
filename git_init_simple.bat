@echo off
chcp 65001 >nul
setlocal

set GITHUB_URL=https://github.com/gucchon001/ebis_bq.git

echo Initializing Git repository...
git init

echo Setting remote origin...
git remote add origin %GITHUB_URL%
if errorlevel 1 (
    echo Remote origin already exists, updating URL...
    git remote set-url origin %GITHUB_URL%
)

echo Adding files...
git add .

echo Creating initial commit...
git commit -m "Initial commit"

echo Pushing to master branch...
git push -u origin master

echo Done!
pause
endlocal 