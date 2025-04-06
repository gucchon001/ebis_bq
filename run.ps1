# run.ps1
# メインスクリプト実行ランチャー

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# 変数の初期化
$VENV_PATH = ".\venv"
$DEFAULT_SCRIPT = "src\main.py"
$SCRIPT_TO_RUN = $DEFAULT_SCRIPT

# プロジェクトの基準ディレクトリを取得
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_ROOT

# コマンドライン引数の解析
if ($args.Count -gt 0) {
    if ($args[0] -eq "--help") {
        # ヘルプメッセージの表示
        Write-Host "使用方法:"
        Write-Host "  .\run.ps1 [モジュール名]"
        Write-Host ""
        Write-Host "オプション:"
        Write-Host "  モジュール名   : 実行するPythonスクリプト（拡張子なし）"
        Write-Host "  --help       : このヘルプを表示します。"
        Write-Host ""
        Write-Host "例:"
        Write-Host "  .\run.ps1"
        Write-Host "  .\run.ps1 utils\spreadsheet"
        exit 0
    } else {
        $SCRIPT_TO_RUN = "src\$($args[0]).py"
    }
}

# 仮想環境が存在するか確認
if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
    Write-Host "[INFO] 仮想環境をアクティブ化しています..." -ForegroundColor Green
    & "$VENV_PATH\Scripts\Activate.ps1"
} else {
    Write-Host "[ERROR] 仮想環境が見つかりません: $VENV_PATH" -ForegroundColor Red
    Write-Host "仮想環境を作成するか、正しいパスを設定してください。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# スクリプトが存在するか確認
if (Test-Path $SCRIPT_TO_RUN) {
    Write-Host "[INFO] スクリプトを実行しています: $SCRIPT_TO_RUN" -ForegroundColor Green
    # PYTHONPATHを設定してプロジェクトルートを参照できるようにする
    $env:PYTHONPATH = $PROJECT_ROOT
    python $SCRIPT_TO_RUN
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] スクリプトの実行中にエラーが発生しました。" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
} else {
    Write-Host "[ERROR] スクリプトが見つかりません: $SCRIPT_TO_RUN" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 仮想環境をディアクティブ化
Write-Host "[INFO] 仮想環境をディアクティブ化しています..." -ForegroundColor Green
if (Test-Path Function:\deactivate) {
    deactivate
}

Write-Host "[INFO] 実行が完了しました。" -ForegroundColor Green
Read-Host "Enterキーを押して終了します"
