# update_libraries.ps1
# Pythonライブラリアップデートツール

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# スクリプトが実行されたディレクトリを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "===== Python ライブラリアップデートツール =====" -ForegroundColor Cyan
Write-Host ""

# Python が利用可能か確認
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python検出: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "エラー: Python が見つかりません。" -ForegroundColor Red
    Write-Host "Python がインストールされていることを確認してください。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 仮想環境の存在確認
if (-not (Test-Path "venv")) {
    Write-Host "仮想環境が見つかりません。新しく作成します..." -ForegroundColor Yellow
    try {
        python -m venv venv
        Write-Host "仮想環境を作成しました。" -ForegroundColor Green
    }
    catch {
        Write-Host "仮想環境の作成に失敗しました。" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
}

# 仮想環境をアクティベート
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "仮想環境をアクティベートしました。" -ForegroundColor Green
    
    # PYTHONPATHを設定してプロジェクトルートを参照できるようにする
    $env:PYTHONPATH = $scriptDir
}
catch {
    Write-Host "仮想環境のアクティベートに失敗しました。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# pip のアップグレード
Write-Host "pip をアップグレードしています..." -ForegroundColor Yellow
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip のアップグレードに失敗しました。" -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# requirements.txt の存在確認
if (-not (Test-Path "requirements.txt")) {
    Write-Host "requirements.txt が見つかりません。" -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# ライブラリのアップデート
Write-Host ""
Write-Host "ライブラリをアップデートしています..." -ForegroundColor Yellow
pip install -r requirements.txt --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "ライブラリのアップデートに失敗しました。" -ForegroundColor Red
    if (Test-Path Function:\deactivate) {
        deactivate
    }
    Read-Host "Enterキーを押して終了します"
    exit 1
}

Write-Host ""
Write-Host "現在インストールされているパッケージ一覧:" -ForegroundColor Cyan
pip list
Write-Host ""
Write-Host "ライブラリのアップデートが完了しました。" -ForegroundColor Green

# 仮想環境を非アクティベート
if (Test-Path Function:\deactivate) {
    deactivate
}

Write-Host ""
Write-Host "処理を終了します。" -ForegroundColor Green
Read-Host "Enterキーを押して終了します" 