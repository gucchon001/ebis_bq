@echo off
chcp 65001 >nul
setlocal

echo ===== ライブラリ更新ツール =====
echo.

rem PowerShellスクリプトを実行
powershell -ExecutionPolicy Bypass -NoProfile -Command ^
"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ^
[Console]::InputEncoding = [System.Text.Encoding]::UTF8; ^
& {param($scriptDir) ^
$VENV_PATH = Join-Path $scriptDir 'venv'; ^
$REQUIREMENTS_PATH = Join-Path $scriptDir 'requirements.txt'; ^
$PIP_UPGRADE_LIST = @('pip', 'setuptools', 'wheel'); ^
^
# 仮想環境が存在するか確認 ^
if (Test-Path (Join-Path $VENV_PATH 'Scripts\Activate.ps1')) { ^
    Write-Host '[INFO] 仮想環境をアクティブ化しています...' -ForegroundColor Green; ^
    & (Join-Path $VENV_PATH 'Scripts\Activate.ps1'); ^
} else { ^
    Write-Host '[INFO] 仮想環境を作成しています...' -ForegroundColor Green; ^
    python -m venv $VENV_PATH; ^
    ^
    if (Test-Path (Join-Path $VENV_PATH 'Scripts\Activate.ps1')) { ^
        Write-Host '[INFO] 仮想環境をアクティブ化しています...' -ForegroundColor Green; ^
        & (Join-Path $VENV_PATH 'Scripts\Activate.ps1'); ^
    } else { ^
        Write-Host '[ERROR] 仮想環境の作成に失敗しました。' -ForegroundColor Red; ^
        Read-Host 'Enterキーを押して終了します'; ^
        exit 1; ^
    } ^
} ^
^
# pipとsetuptoolsを最新にアップデート ^
Write-Host '[INFO] pipとその他の基本パッケージを更新しています...' -ForegroundColor Green; ^
foreach ($pkg in $PIP_UPGRADE_LIST) { ^
    python -m pip install --upgrade $pkg; ^
    if ($LASTEXITCODE -ne 0) { ^
        Write-Host '[ERROR] 基本パッケージの更新に失敗しました: ' $pkg -ForegroundColor Red; ^
        Write-Host '続行しますが、問題が発生する可能性があります。' -ForegroundColor Yellow; ^
    } ^
} ^
^
# requirements.txtが存在するか確認 ^
if (Test-Path $REQUIREMENTS_PATH) { ^
    Write-Host '[INFO] ライブラリをインストールしています...' -ForegroundColor Green; ^
    python -m pip install -r $REQUIREMENTS_PATH; ^
    ^
    if ($LASTEXITCODE -ne 0) { ^
        Write-Host '[ERROR] ライブラリのインストールに失敗しました。' -ForegroundColor Red; ^
        Read-Host 'Enterキーを押して終了します'; ^
        exit 1; ^
    } ^
} else { ^
    Write-Host '[ERROR] requirements.txtが見つかりません: ' $REQUIREMENTS_PATH -ForegroundColor Red; ^
    Read-Host 'Enterキーを押して終了します'; ^
    exit 1; ^
} ^
^
# 現在のインストール済みパッケージを表示 ^
Write-Host '[INFO] 現在インストールされているパッケージ:' -ForegroundColor Green; ^
python -m pip list; ^
^
# 仮想環境をディアクティブ化 ^
if (Get-Command deactivate -ErrorAction SilentlyContinue) { ^
    Write-Host '[INFO] 仮想環境をディアクティブ化しています...' -ForegroundColor Green; ^
    deactivate; ^
} ^
^
Write-Host '[INFO] ライブラリの更新が完了しました。' -ForegroundColor Green; ^
Read-Host 'Enterキーを押して終了します'; ^
} '%~dp0'"

endlocal 