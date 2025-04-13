# run_dev.ps1
# 開発環境用スクリプト実行ランチャー

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# 変数の初期化
$VENV_PATH = ".\venv"
$PYTHON_CMD = "python"
$PIP_CMD = "pip"
$DEFAULT_SCRIPT = "src.main"
$SCRIPT_TO_RUN = $DEFAULT_SCRIPT
$APP_ENV = $null

# プロジェクトの基準ディレクトリを取得
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_ROOT

# コマンドライン引数の解析
$i = 0
while ($i -lt $args.Count) {
    if ($args[$i] -eq "-m" -and $i+1 -lt $args.Count) {
        $SCRIPT_TO_RUN = "src." + $args[$i+1]
        $i += 2
    } elseif ($args[$i] -eq "--help") {
        # ヘルプメッセージの表示
        Write-Host "使用方法:"
        Write-Host "  .\run_dev.ps1 [オプション]"
        Write-Host ""
        Write-Host "オプション:"
        Write-Host "  -m モジュール名    : 実行するPythonモジュールを指定します"
        Write-Host "  --help             : このヘルプを表示します。"
        Write-Host ""
        Write-Host "例:"
        Write-Host "  .\run_dev.ps1"
        Write-Host "  .\run_dev.ps1 -m utils.spreadsheet"
        exit 0
    } else {
        $i++
    }
}

# 引数がない場合、環境を選択するプロンプトを表示
if ($args.Count -eq 0) {
    Write-Host "実行環境を選択してください:" -ForegroundColor Cyan
    Write-Host "  1. Development (dev)"
    Write-Host "  2. Production (prd)"
    $choice = Read-Host "選択肢を入力してください (1/2)"
    
    if ($choice -eq "1") {
        $APP_ENV = "development"
    } elseif ($choice -eq "2") {
        $APP_ENV = "production"
    } else {
        Write-Host "Error: 無効な選択肢です。再実行してください。" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
}

# Pythonがインストールされているか確認
try {
    & $PYTHON_CMD --version | Out-Null
} catch {
    Write-Host "Error: Python がインストールされていないか、環境パスが設定されていません。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 仮想環境がなければ作成
if (-not (Test-Path "$VENV_PATH\Scripts\Activate.ps1")) {
    Write-Host "[LOG] 仮想環境が存在しません。作成中..." -ForegroundColor Yellow
    & $PYTHON_CMD -m venv $VENV_PATH
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: 仮想環境の作成に失敗しました。" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
    Write-Host "[LOG] 仮想環境が正常に作成されました。" -ForegroundColor Green
}

# 仮想環境をアクティベート
if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
    & "$VENV_PATH\Scripts\Activate.ps1"
} else {
    Write-Host "Error: 仮想環境の有効化に失敗しました。activate スクリプトが見つかりません。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# PYTHONPATHを設定してプロジェクトルートを参照できるようにする
$env:PYTHONPATH = $PROJECT_ROOT

# requirements.txtの存在確認
if (-not (Test-Path "requirements.txt")) {
    Write-Host "Error: requirements.txt が見つかりません。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 必要に応じてパッケージをインストール
$currentHash = Get-FileHash -Path "requirements.txt" -Algorithm SHA256
$currentHashValue = $currentHash.Hash

if (Test-Path ".req_hash") {
    $storedHash = Get-Content -Path ".req_hash" -Raw
} else {
    $storedHash = ""
}

if ($currentHashValue -ne $storedHash) {
    Write-Host "[LOG] 必要なパッケージをインストール中..." -ForegroundColor Yellow
    & $PIP_CMD install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: パッケージのインストールに失敗しました。" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
    $currentHashValue | Out-File -FilePath ".req_hash" -NoNewline
}

# スクリプトを実行
Write-Host "[LOG] 環境: $APP_ENV" -ForegroundColor Cyan
Write-Host "[LOG] 実行スクリプト: $SCRIPT_TO_RUN" -ForegroundColor Cyan

# 環境変数を設定
$env:APP_ENV = $APP_ENV

# Pythonスクリプトを実行
& $PYTHON_CMD -m $SCRIPT_TO_RUN
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: スクリプトの実行に失敗しました。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 仮想環境を非アクティベート
if (Test-Path Function:\deactivate) {
    deactivate
}

Write-Host "[INFO] 実行が完了しました。" -ForegroundColor Green
Read-Host "Enterキーを押して終了します"
