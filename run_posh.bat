@echo off
chcp 65001 >nul
setlocal

echo ===== メインスクリプト実行ツール =====
echo.

rem PowerShellスクリプトを実行
powershell -ExecutionPolicy Bypass -NoProfile -Command ^
"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ^
[Console]::InputEncoding = [System.Text.Encoding]::UTF8; ^
& {param($scriptDir) ^
$VENV_PATH = Join-Path $scriptDir 'venv'; ^
$DEFAULT_SCRIPT = 'src\main.py'; ^
$SCRIPT_TO_RUN = $DEFAULT_SCRIPT; ^
^
# コマンドライン引数の解析 ^
$args = $args; ^
if ($args.Count -gt 0) { ^
    if ($args[0] -eq '--help') { ^
        # ヘルプメッセージの表示 ^
        Write-Host '使用方法:'; ^
        Write-Host '  .\run_posh.bat [モジュール名]'; ^
        Write-Host ''; ^
        Write-Host 'オプション:'; ^
        Write-Host '  モジュール名   : 実行するPythonスクリプト（拡張子なし）'; ^
        Write-Host '  --help       : このヘルプを表示します。'; ^
        Write-Host ''; ^
        Write-Host '例:'; ^
        Write-Host '  .\run_posh.bat'; ^
        Write-Host '  .\run_posh.bat utils\spreadsheet'; ^
        exit 0; ^
    } else { ^
        $SCRIPT_TO_RUN = 'src\' + $args[0] + '.py'; ^
    } ^
} ^
^
# 仮想環境が存在するか確認 ^
if (Test-Path (Join-Path $VENV_PATH 'Scripts\Activate.ps1')) { ^
    Write-Host '[INFO] 仮想環境をアクティブ化しています...' -ForegroundColor Green; ^
    & (Join-Path $VENV_PATH 'Scripts\Activate.ps1'); ^
} else { ^
    Write-Host '[ERROR] 仮想環境が見つかりません: ' $VENV_PATH -ForegroundColor Red; ^
    Write-Host '仮想環境を作成するか、正しいパスを設定してください。' -ForegroundColor Red; ^
    Read-Host 'Enterキーを押して終了します'; ^
    exit 1; ^
} ^
^
# スクリプトが存在するか確認 ^
if (Test-Path $SCRIPT_TO_RUN) { ^
    Write-Host '[INFO] スクリプトを実行しています: ' $SCRIPT_TO_RUN -ForegroundColor Green; ^
    python $SCRIPT_TO_RUN; ^
    if ($LASTEXITCODE -ne 0) { ^
        Write-Host '[ERROR] スクリプトの実行中にエラーが発生しました。' -ForegroundColor Red; ^
        Read-Host 'Enterキーを押して終了します'; ^
        exit 1; ^
    } ^
} else { ^
    Write-Host '[ERROR] スクリプトが見つかりません: ' $SCRIPT_TO_RUN -ForegroundColor Red; ^
    Read-Host 'Enterキーを押して終了します'; ^
    exit 1; ^
} ^
^
# 仮想環境をディアクティブ化 ^
if (Get-Command deactivate -ErrorAction SilentlyContinue) { ^
    Write-Host '[INFO] 仮想環境をディアクティブ化しています...' -ForegroundColor Green; ^
    deactivate; ^
} ^
^
Write-Host '[INFO] 実行が完了しました。' -ForegroundColor Green; ^
Read-Host 'Enterキーを押して終了します'; ^
} '%~dp0' $args"

endlocal 