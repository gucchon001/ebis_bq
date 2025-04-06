# run_real_tests.ps1
# 実際の接続テストを簡単に実行するためのヘルパースクリプト
#
# 使用方法:
#   .\run_real_tests.ps1 [-SkipOpenAI] [-TestPath <PATH>] [-TestName <TEST_NAME>] [-ApiKey <KEY>]
#
# パラメータ:
#   -SkipOpenAI     : OpenAI APIテストをスキップする
#   -TestPath <PATH> : テスト対象のGitリポジトリパス（デフォルト: カレントディレクトリ）
#   -TestName <NAME> : 特定のテスト名を指定して実行する
#   -ApiKey <KEY>    : OpenAI APIキー（環境変数OPENAI_API_KEYが設定されていない場合に使用）
#
# このスクリプトは環境変数を設定し、指定されたテストを実行します。

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# パラメータの定義
param(
    [switch]$SkipOpenAI,
    [string]$TestPath = ".",
    [string]$TestName,
    [string]$ApiKey
)

# スクリプトが実行されたディレクトリを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# testsディレクトリへのパスを作成
$testsDir = Join-Path $scriptDir "tests"

# テストファイルパスの作成
$testFile = Join-Path $testsDir "test_real_integration.py"

if (-not (Test-Path $testFile)) {
    Write-Host "エラー: テストファイルが見つかりません: $testFile" -ForegroundColor Red
    exit 1
}

# 環境変数の設定
$env:TEST_REPO_PATH = (Resolve-Path $TestPath).Path
$env:SKIP_OPENAI_TESTS = if ($SkipOpenAI) { "true" } else { "false" }

# APIキーが指定されていて、まだ環境変数が設定されていない場合
if ($ApiKey -and -not $env:OPENAI_API_KEY) {
    $env:OPENAI_API_KEY = $ApiKey
}

# 実行コマンドの構築
$command = "python -m pytest $testFile -v"

# 特定のテストが指定されている場合
if ($TestName) {
    $command = "python -m pytest ${testFile}::TestRealIntegration::$TestName -v"
}

# テスト実行前の情報表示
Write-Host ""
Write-Host "=== 接続テスト実行 ===" -ForegroundColor Cyan
Write-Host "テスト対象リポジトリ: $($env:TEST_REPO_PATH)" -ForegroundColor Cyan
Write-Host "OpenAIテスト: $(if ($SkipOpenAI) {"スキップ"} else {"実行"})" -ForegroundColor Cyan
if ($TestName) {
    Write-Host "テスト名: $TestName" -ForegroundColor Cyan
} else {
    Write-Host "すべてのテストを実行します" -ForegroundColor Cyan
}
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""

try {
    # コマンド実行
    Write-Host "実行コマンド: $command" -ForegroundColor Green
    $result = Invoke-Expression $command
    
    # 終了コードに基づいて結果を表示
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ テストが正常に完了しました" -ForegroundColor Green
    } else {
        Write-Host "`n❌ テストが失敗しました（終了コード: $LASTEXITCODE）" -ForegroundColor Red
    }
    
    exit $LASTEXITCODE
} catch {
    Write-Host "`n❌ テスト実行中にエラーが発生しました: $_" -ForegroundColor Red
    exit 1
} 