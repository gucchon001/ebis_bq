@echo off
chcp 65001 >nul

REM 仮想環境のパスを設定
set "VENV_PATH=.\venv"
set "DEFAULT_SCRIPT=src\main.py"
set "SCRIPT_TO_RUN=%DEFAULT_SCRIPT%"

REM プロジェクトの基準ディレクトリを取得
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

REM コマンドライン引数の解析
if "%~1" NEQ "" (
    set "SCRIPT_TO_RUN=src\%~1.py"
)

REM ヘルプメッセージの表示
if "%~1"=="--help" (
    echo 使用方法:
    echo   run.bat [モジュール名]
    echo
    echo オプション:
    echo   モジュール名   : 実行するPythonスクリプト（拡張子なし）
    echo   --help       : このヘルプを表示します。
    echo
    echo 例:
    echo   run.bat
    echo   run.bat utils\spreadsheet
    exit /b 0
)

REM 仮想環境が存在するか確認
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] 仮想環境をアクティブ化しています...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [ERROR] 仮想環境が見つかりません: %VENV_PATH%
    echo 仮想環境を作成するか、正しいパスを設定してください。
    pause
    exit /b 1
)

REM スクリプトが存在するか確認
if exist "%SCRIPT_TO_RUN%" (
    echo [INFO] スクリプトを実行しています: %SCRIPT_TO_RUN%
    python "%SCRIPT_TO_RUN%"
    if errorlevel 1 (
        echo [ERROR] スクリプトの実行中にエラーが発生しました。
        pause
        exit /b 1
    )
) else (
    echo [ERROR] スクリプトが見つかりません: %SCRIPT_TO_RUN%
    pause
    exit /b 1
)

REM 仮想環境をディアクティブ化
echo [INFO] 仮想環境をディアクティブ化しています...
deactivate

echo [INFO] 実行が完了しました。
pause
