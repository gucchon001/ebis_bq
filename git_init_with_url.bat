@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ===== Gitリポジトリ初期化ツール =====

rem GitHubデスクトップが自動起動しないようにする環境変数設定
set "GIT_OPTIONAL_LOCKS=0"
set "EDITOR=notepad"
set "GIT_EDITOR=notepad"
set "GIT_TERMINAL_PROMPT=1"
set "GIT_CREDENTIAL_HELPER="

rem 特定のリポジトリURLを設定
set "GITHUB_URL=https://github.com/gucchon001/ebis_bq.git"

echo Gitリポジトリを初期化しています...
git -c credential.helper="" -c core.editor=notepad -c core.autocrlf=true init
if errorlevel 1 (
    echo エラー: リポジトリの初期化に失敗しました。
    goto END
)

echo.
echo GitHub リポジトリURLを設定: %GITHUB_URL%

echo リモートリポジトリを設定しています...
git -c credential.helper="" remote add origin %GITHUB_URL%
if errorlevel 1 (
    echo エラー: リモートリポジトリの設定に失敗しました。
    goto END
)

echo 初期コミットを実行しています...
git add .
git -c credential.helper="" commit -m "Initial commit"
if errorlevel 1 (
    echo エラー: コミットに失敗しました。
    goto END
)

echo プッシュを実行しています...
git -c credential.helper="" push -u origin main
if errorlevel 1 (
    echo エラー: プッシュに失敗しました。
    goto END
)

echo.
echo リポジトリの初期化と初期コミットが完了しました。
echo リモートリポジトリURL: %GITHUB_URL%

:END
echo.
pause
endlocal 