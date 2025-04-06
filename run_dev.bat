@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

rem Initialize environment variables
set "VENV_PATH=.\venv"
set "PYTHON_CMD=python"
set "PIP_CMD=pip"
set "DEFAULT_SCRIPT=src.main"
set "SCRIPT_TO_RUN=%DEFAULT_SCRIPT%"
set "APP_ENV="

rem プロジェクトの基準ディレクトリを取得
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

rem Parse command line arguments
:parse_args
if "%~1"=="-m" (
    set "SCRIPT_TO_RUN=src.%~2"
    shift
    shift
    goto parse_args
)

rem Display help message if --help is provided
if "%~1"=="--help" (
    echo 使用方法:
    echo   run_dev.bat [オプション]
    echo
    echo オプション:
    echo   -m モジュール名    : 実行するPythonモジュールを指定します
    echo   --help             : このヘルプを表示します。
    echo
    echo 例:
    echo   run_dev.bat
    echo   run_dev.bat -m utils.spreadsheet
    goto END
)

rem If no arguments are provided, prompt the user for environment
if "%~1"=="" (
    echo 実行環境を選択してください:
    echo   1. Development (dev)
    echo   2. Production (prd)
    set /p "CHOICE=選択肢を入力してください (1/2): "
    if "%CHOICE%"=="1" (
        set "APP_ENV=development"
    )
    if "%CHOICE%"=="2" (
        set "APP_ENV=production"
    )
    if not defined APP_ENV (
        echo Error: 無効な選択肢です。再実行してください。
        exit /b 1
    )
)

rem Check if Python is installed
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python がインストールされていないか、環境パスが設定されていません。
    pause
    exit /b 1
)

rem Create virtual environment if it doesn't exist
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [LOG] 仮想環境が存在しません。作成中...
    %PYTHON_CMD% -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo Error: 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
    echo [LOG] 仮想環境が正常に作成されました。
)

rem Activate virtual environment
if exist "%VENV_PATH%\Scripts\activate" (
    call "%VENV_PATH%\Scripts\activate"
) else (
    echo Error: 仮想環境の有効化に失敗しました。activate スクリプトが見つかりません。
    pause
    exit /b 1
)

rem Check requirements.txt
if not exist requirements.txt (
    echo Error: requirements.txt が見つかりません。
    pause
    exit /b 1
)

rem Install requirements if needed
for /f "skip=1 delims=" %%a in ('certutil -hashfile requirements.txt SHA256') do if not defined CURRENT_HASH set "CURRENT_HASH=%%a"

if exist .req_hash (
    set /p STORED_HASH=<.req_hash
) else (
    set "STORED_HASH="
)

if not "%CURRENT_HASH%"=="%STORED_HASH%" (
    echo [LOG] 必要なパッケージをインストール中...
    %PIP_CMD% install -r requirements.txt
    if errorlevel 1 (
        echo Error: パッケージのインストールに失敗しました。
        pause
        exit /b 1
    )
    echo %CURRENT_HASH%>.req_hash
)

rem Run the script
echo [LOG] 環境: %APP_ENV%
echo [LOG] 実行スクリプト: %SCRIPT_TO_RUN%

rem 環境変数を設定
set "APP_ENV=%APP_ENV%"

rem Pythonスクリプトを実行
%PYTHON_CMD% -m %SCRIPT_TO_RUN%
if errorlevel 1 (
    echo Error: スクリプトの実行に失敗しました。
    pause
    exit /b 1
)

:END
endlocal
