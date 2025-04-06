# シンプル開発環境スクリプト
$ErrorActionPreference = "Stop"

# スクリプトの基本設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# タイトル表示
Write-Host "===== シンプル開発実行ツール =====" -ForegroundColor Cyan
Write-Host ""

# 仮想環境を有効化
$VENV_PATH = ".\venv"
if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
    & "$VENV_PATH\Scripts\Activate.ps1"
    Write-Host "仮想環境を有効化しました" -ForegroundColor Green
} else {
    Write-Host "仮想環境が見つかりません。作成してください。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# モジュール実行
$MODULE = "src.main"
Write-Host "実行するモジュール: $MODULE" -ForegroundColor Yellow
python -m $MODULE

# 仮想環境を無効化
deactivate

Write-Host ""
Write-Host "実行が完了しました" -ForegroundColor Green
Read-Host "Enterキーを押して終了します" 