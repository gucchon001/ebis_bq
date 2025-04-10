# テスト実行ランチャー PowerShellスクリプト
# 実行方法: .\run_tests.ps1

# エラー発生時に即座に停止
$ErrorActionPreference = "Stop"

# PowerShellスクリプトが実行されたディレクトリを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# UTF-8を強制
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# タイトルと説明の表示
Write-Host "===== テスト実行ツール =====" -ForegroundColor Cyan
Write-Host ""

# Pythonが利用可能か確認
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python検出: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "エラー: Pythonが見つかりません。インストールしてください。" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 仮想環境の存在を確認
if (-not (Test-Path "venv")) {
    Write-Host "仮想環境が見つかりません。新しく作成します..." -ForegroundColor Yellow
    try {
        python -m venv venv
        Write-Host "仮想環境が作成されました" -ForegroundColor Green
    }
    catch {
        Write-Host "仮想環境の作成に失敗しました: $_" -ForegroundColor Red
        Read-Host "Enterキーを押して終了します"
        exit 1
    }
}

# 仮想環境をアクティベート
try {
    if ($PSVersionTable.PSEdition -eq "Core") {
        # PowerShell Core
        & "./venv/Scripts/Activate.ps1"
    }
    else {
        # Windows PowerShell
        & "./venv/Scripts/Activate.ps1"
    }
    
    # PYTHONPATHを設定してプロジェクトルートを参照できるようにする
    $env:PYTHONPATH = $scriptDir
    
    Write-Host "仮想環境が有効化されました" -ForegroundColor Green
}
catch {
    Write-Host "仮想環境のアクティベートに失敗しました: $_" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 必要なパッケージのインストール確認
try {
    $testImport = python -c "import pytest" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pytestがインストールされていません。インストールします..." -ForegroundColor Yellow
        python -m pip install pytest pytest-html
        if ($LASTEXITCODE -ne 0) {
            Write-Host "pytestのインストールに失敗しました" -ForegroundColor Red
            Read-Host "Enterキーを押して終了します"
            exit 1
        }
    }
}
catch {
    Write-Host "パッケージのインストール確認中にエラーが発生しました: $_" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します"
    exit 1
}

# 結果ディレクトリの作成
if (-not (Test-Path "tests\results")) {
    New-Item -Path "tests\results" -ItemType Directory -Force | Out-Null
    Write-Host "tests\resultsディレクトリを作成しました" -ForegroundColor Green
}

# メイン処理ループ
function Show-Menu {
    Write-Host ""
    Write-Host "実行モードを選択してください:" -ForegroundColor Cyan
    Write-Host "1: すべてのテストを実行"
    Write-Host "2: スキップマークを無視してすべてのテストを実行"
    Write-Host "3: 個別のテストを実行"
    Write-Host "4: テスト結果サマリーを表示"
    Write-Host "5: テストレポートをエクスポート"
    Write-Host "6: 終了"
    Write-Host ""
    
    $selection = Read-Host "選択 (1-6)"
    return $selection
}

# すべてのテストを実行
function Run-AllTests {
    Write-Host ""
    Write-Host "すべてのテストを実行中..." -ForegroundColor Cyan
    Write-Host ""
    
    # test_runner.pyを使用してテストを実行
    python -m src.utils.test_runner tests -v --report
    
    Write-Host ""
    Write-Host "すべてのテストが完了しました。一部のテストはエラーによりスキップされた可能性があります。" -ForegroundColor Yellow
    Write-Host "テスト結果はtests\resultsフォルダに保存されています。"
    Write-Host ""
    
    $showSummary = Read-Host "テスト結果サマリーを表示しますか？ (Y/N)"
    if ($showSummary -eq "Y" -or $showSummary -eq "y") {
        Show-TestSummary
    }
}

# スキップマークを無視してすべてのテストを実行
function Run-AllTestsIncludingSkipped {
    Write-Host ""
    Write-Host "スキップマークを無視してすべてのテストを実行中..." -ForegroundColor Cyan
    Write-Host ""
    
    # test_runner.pyを使用してテストを実行 (スキップマークを無視)
    python -m src.utils.test_runner tests -v --report --no-skip --run-xfail
    
    Write-Host ""
    Write-Host "すべてのテスト（スキップされたものを含む）が完了しました。" -ForegroundColor Yellow
    Write-Host "テスト結果はtests\resultsフォルダに保存されています。"
    Write-Host ""
    
    $showSummary = Read-Host "テスト結果サマリーを表示しますか？ (Y/N)"
    if ($showSummary -eq "Y" -or $showSummary -eq "y") {
        Show-TestSummary
    }
}

# 個別のテストを選択して実行
function Select-TestToRun {
    Write-Host ""
    Write-Host "実行するテストを選択してください:" -ForegroundColor Cyan
    
    $testFiles = Get-ChildItem -Path "tests\test_*.py"
    $fileMap = @{}
    
    for ($i = 1; $i -le $testFiles.Count; $i++) {
        $fileName = $testFiles[$i-1].BaseName
        Write-Host "$i`: $fileName"
        $fileMap[$i] = $testFiles[$i-1].FullName
    }
    
    $backOption = $testFiles.Count + 1
    Write-Host "$backOption`: 戻る"
    Write-Host ""
    
    [int]$testChoice = Read-Host "テスト番号を選択してください (1-$backOption)"
    
    if ($testChoice -eq $backOption) {
        return
    }
    
    if ($testChoice -lt 1 -or $testChoice -gt $testFiles.Count) {
        Write-Host "無効な選択です。もう一度試してください。" -ForegroundColor Red
        return
    }
    
    $selectedTest = $fileMap[$testChoice]
    Write-Host ""
    Write-Host "$selectedTest を実行しています..." -ForegroundColor Cyan
    Write-Host ""
    
    # test_runner.pyを使用して特定のテストを実行
    python -m src.utils.test_runner "$selectedTest" -v --report
    
    Write-Host ""
    Write-Host "テストが完了しました。一部のテストはエラーによりスキップされた可能性があります。" -ForegroundColor Yellow
    Write-Host "テスト結果はtests\resultsフォルダに保存されています。"
    Write-Host ""
    
    $showSummary = Read-Host "テスト結果サマリーを表示しますか？ (Y/N)"
    if ($showSummary -eq "Y" -or $showSummary -eq "y") {
        Show-TestSummary
    }
}

# テスト結果サマリーを表示
function Show-TestSummary {
    Write-Host ""
    Write-Host "テスト結果サマリーを生成しています..." -ForegroundColor Cyan
    Write-Host ""
    
    # サマリースクリプトの実行
    python -m src.utils.test_summary
    
    Write-Host ""
    Read-Host "Enterキーを押してメニューに戻ります"
}

# テスト結果レポートをエクスポート
function Export-TestReport {
    Write-Host ""
    Write-Host "テスト結果レポートを生成しています..." -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "出力形式を選択してください:"
    Write-Host "1: テキスト形式 (TXT)"
    Write-Host "2: JSON形式"
    Write-Host "3: 両方"
    Write-Host "4: 戻る"
    Write-Host ""
    
    $formatChoice = Read-Host "選択 (1-4)"
    
    switch ($formatChoice) {
        "1" {
            python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path = generator.export_summary(format='txt'); print('テスト結果が保存されました: ' + str(path))"
        }
        "2" {
            python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path = generator.export_summary(format='json'); print('テスト結果が保存されました: ' + str(path))"
        }
        "3" {
            python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path1 = generator.export_summary(format='txt'); path2 = generator.export_summary(format='json'); print('テスト結果が保存されました: ' + str(path1) + ' および ' + str(path2))"
        }
        "4" {
            # 何もしない - メニューに戻る
        }
        default {
            Write-Host "無効な選択です。もう一度試してください。" -ForegroundColor Red
        }
    }
}

# メインループ
$running = $true
while ($running) {
    $selection = Show-Menu
    
    switch ($selection) {
        "1" { Run-AllTests }
        "2" { Run-AllTestsIncludingSkipped }
        "3" { Select-TestToRun }
        "4" { Show-TestSummary }
        "5" { Export-TestReport }
        "6" { 
            $running = $false
            Write-Host "プログラムを終了します..." -ForegroundColor Yellow
        }
        default {
            Write-Host "無効な選択です。1から6の数字を入力してください。" -ForegroundColor Red
        }
    }
}

# 仮想環境を非アクティベート
try {
    deactivate
}
catch {
    # エラーを無視
}

Write-Host ""
Write-Host "処理が完了しました。" -ForegroundColor Green
Read-Host "Enterキーを押して終了します"
