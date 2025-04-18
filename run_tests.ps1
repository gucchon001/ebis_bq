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
    python -c "import pytest" 2>&1
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
    Write-Host "6: 中間ファイルをクリーンアップ"
    Write-Host "7: 終了"
    Write-Host ""
    
    $selection = Read-Host "選択 (1-7)"
    return $selection
}

# すべてのテストを実行
function Invoke-AllTests {
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
function Invoke-AllTestsIncludingSkipped {
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
    Write-Host "個別テスト実行モードを選択します..." -ForegroundColor Cyan
    Write-Host ""
    
    # 選択オプションを表示
    Write-Host "実行タイプを選択してください:" -ForegroundColor Yellow
    Write-Host "1: フォルダを選択"
    Write-Host "2: ファイルを選択"
    Write-Host "0: 戻る"
    
    $choice = Read-Host "`n選択してください (0-2)"
    
    switch ($choice) {
        "0" { return }
        "1" { Select-TestFolder }
        "2" { Select-TestFile }
        default {
            Write-Host "無効な選択です。もう一度お試しください。" -ForegroundColor Red
        }
    }
}

# テストフォルダを選択して実行
function Select-TestFolder {
    $testDir = Join-Path $scriptDir "tests\test_file"
    Write-Host "`n検索ディレクトリ: $testDir" -ForegroundColor Gray
    
    if (-not (Test-Path $testDir)) {
        Write-Host "エラー: テストディレクトリが存在しません: $testDir" -ForegroundColor Red
        return
    }
    
    # フォルダを取得（隠しフォルダを除く）
    $folders = Get-ChildItem -Path $testDir -Directory | Where-Object { $_.Name -notlike ".*" } | Select-Object -ExpandProperty Name | Sort-Object
    
    if ($folders.Count -eq 0) {
        Write-Host "テストフォルダが見つかりません。" -ForegroundColor Yellow
        return
    }
    
    Write-Host "`n利用可能なテストフォルダ:" -ForegroundColor Cyan
    for ($i = 1; $i -le $folders.Count; $i++) {
        Write-Host "$i`: $($folders[$i-1])"
    }
    Write-Host "0: 戻る"
    
    $folderChoice = Read-Host "`nフォルダを選択してください (0-$($folders.Count))"
    
    if ($folderChoice -eq "0") {
        return
    }
    
    try {
        $folderIndex = [int]$folderChoice - 1
        if ($folderIndex -ge 0 -and $folderIndex -lt $folders.Count) {
            $selectedFolder = $folders[$folderIndex]
            $folderPath = Join-Path $testDir $selectedFolder
            
            Write-Host "`nフォルダ '$selectedFolder' のテストを実行します..." -ForegroundColor Cyan
            
            # 追加オプションの選択
            Write-Host "`n実行オプションを選択してください:" -ForegroundColor Yellow
            Write-Host "1: 通常実行"
            Write-Host "2: 詳細出力モード"
            Write-Host "3: スキップマークを無視して実行"
            Write-Host "0: 戻る"
            
            $optionChoice = Read-Host "`n選択してください (0-3)"
            
            if ($optionChoice -eq "0") {
                return
            }
            
            # 引数を別々に設定
            $folderArg = $folderPath
            $verboseArg = "-v"
            $reportArg = "--report"
            
            # オプションに応じて追加引数を設定
            $additionalArgs = @()
            switch ($optionChoice) {
                "1" { 
                    # 通常実行 - 追加引数なし
                }
                "2" { 
                    # 詳細出力モード
                    $additionalArgs += "--html"
                }
                "3" { 
                    # スキップマーク無視
                    $additionalArgs += "--no-skip"
                    $additionalArgs += "--run-xfail"
                }
                default { 
                    # デフォルトは通常実行
                }
            }
            
            # test_runner.pyを使用してテストを実行 - 引数を個別に渡す
            Write-Host "テストを実行します: $folderPath"
            $argsList = @($folderArg, $verboseArg, $reportArg) + $additionalArgs
            $argsString = $argsList -join " "
            Write-Host "実行コマンド: python -m src.utils.test_runner $argsString" -ForegroundColor Gray
            
            # Start-Processを使用して正しく引数を渡す
            & python -m src.utils.test_runner $folderArg $verboseArg $reportArg @additionalArgs
            
            Write-Host "`nテスト実行が完了しました。" -ForegroundColor Yellow
            Write-Host "テスト結果はtests\resultsフォルダに保存されています。"
            
            # レポート確認のオプション
            $showReport = Read-Host "`nレポートを表示しますか？ (Y/N)"
            if ($showReport -eq "Y" -or $showReport -eq "y") {
                # まずレポートを生成
                python -m src.utils.test_summary --generate-reports
                # 次にフォルダ構造でレポートを表示
                python -m src.utils.test_summary --folder
                
                # クリーンアップオプションを提供
                $cleanupFiles = Read-Host "`n中間ファイルをクリーンアップしますか？ (Y/N)"
                if ($cleanupFiles -eq "Y" -or $cleanupFiles -eq "y") {
                    python -m src.utils.test_summary --cleanup
                    Write-Host "クリーンアップが完了しました" -ForegroundColor Green
                }
            }
        }
        else {
            Write-Host "無効な選択です。もう一度お試しください。" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "数値を入力してください。" -ForegroundColor Red
    }
}

# テストファイルを選択して実行
function Select-TestFile {
    $testDir = Join-Path $scriptDir "tests\test_file"
    Write-Host "`n検索ディレクトリ: $testDir" -ForegroundColor Gray
    
    if (-not (Test-Path $testDir)) {
        Write-Host "エラー: テストディレクトリが存在しません: $testDir" -ForegroundColor Red
        return
    }
    
    # テストファイルを再帰的に収集
    $testFiles = Get-ChildItem -Path $testDir -Recurse -Include "test_*.py" | Sort-Object FullName
    
    if ($testFiles.Count -eq 0) {
        Write-Host "テストファイルが見つかりません。" -ForegroundColor Yellow
        return
    }
    
    Write-Host "`n利用可能なテストファイル:" -ForegroundColor Cyan
    for ($i = 1; $i -le $testFiles.Count; $i++) {
        # テストディレクトリからの相対パスを表示
        $relativePath = $testFiles[$i-1].FullName.Substring($testDir.Length + 1)
        Write-Host "$i`: $relativePath"
    }
    Write-Host "0: 戻る"
    
    $fileChoice = Read-Host "`nファイルを選択してください (0-$($testFiles.Count))"
    
    if ($fileChoice -eq "0") {
        return
    }
    
    try {
        $fileIndex = [int]$fileChoice - 1
        if ($fileIndex -ge 0 -and $fileIndex -lt $testFiles.Count) {
            $selectedFile = $testFiles[$fileIndex].FullName
            $fileName = $testFiles[$fileIndex].Name
            
            Write-Host "`nファイル '$fileName' のテストを実行します..." -ForegroundColor Cyan
            
            # 追加オプションの選択
            Write-Host "`n実行オプションを選択してください:" -ForegroundColor Yellow
            Write-Host "1: 通常実行"
            Write-Host "2: 詳細出力モード"
            Write-Host "3: スキップマークを無視して実行"
            Write-Host "0: 戻る"
            
            $optionChoice = Read-Host "`n選択してください (0-3)"
            
            if ($optionChoice -eq "0") {
                return
            }
            
            # 引数を別々に設定
            $fileArg = $selectedFile
            $verboseArg = "-v"
            $reportArg = "--report"
            
            # オプションに応じて追加引数を設定
            $additionalArgs = @()
            switch ($optionChoice) {
                "1" { 
                    # 通常実行 - 追加引数なし
                }
                "2" { 
                    # 詳細出力モード
                    $additionalArgs += "--html"
                }
                "3" { 
                    # スキップマーク無視
                    $additionalArgs += "--no-skip"
                    $additionalArgs += "--run-xfail"
                }
                default { 
                    # デフォルトは通常実行
                }
            }
            
            # test_runner.pyを使用してテストを実行 - 引数を個別に渡す
            Write-Host "テストを実行します: $selectedFile"
            $argsList = @($fileArg, $verboseArg, $reportArg) + $additionalArgs
            $argsString = $argsList -join " "
            Write-Host "実行コマンド: python -m src.utils.test_runner $argsString" -ForegroundColor Gray
            
            # 引数を個別に渡す
            & python -m src.utils.test_runner $fileArg $verboseArg $reportArg @additionalArgs
            
            Write-Host "`nテスト実行が完了しました。" -ForegroundColor Yellow
            Write-Host "テスト結果はtests\resultsフォルダに保存されています。"
            
            # レポート確認のオプション
            $showReport = Read-Host "`nレポートを表示しますか？ (Y/N)"
            if ($showReport -eq "Y" -or $showReport -eq "y") {
                # まずレポートを生成
                python -m src.utils.test_summary --generate-reports
                # 次にフォルダ構造でレポートを表示
                python -m src.utils.test_summary --folder
                
                # クリーンアップオプションを提供
                $cleanupFiles = Read-Host "`n中間ファイルをクリーンアップしますか？ (Y/N)"
                if ($cleanupFiles -eq "Y" -or $cleanupFiles -eq "y") {
                    python -m src.utils.test_summary --cleanup
                    Write-Host "クリーンアップが完了しました" -ForegroundColor Green
                }
            }
        }
        else {
            Write-Host "無効な選択です。もう一度お試しください。" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "数値を入力してください。" -ForegroundColor Red
    }
}

# テスト結果のサマリーを表示
function Show-TestSummary {
    Write-Host ""
    Write-Host "テスト結果サマリーを表示しています..." -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "表示オプションを選択してください:" -ForegroundColor Yellow
    Write-Host "1: 基本サマリー表示"
    Write-Host "2: 詳細サマリー表示"
    Write-Host "3: フォルダ構造で表示"
    Write-Host "4: 中間ファイルをクリーンアップ"
    Write-Host "5: 戻る"
    Write-Host ""
    
    $summaryChoice = Read-Host "選択 (1-5)"
    
    switch ($summaryChoice) {
        "1" { 
            # 基本サマリーの表示
            python -m src.utils.test_summary --generate-reports
            python -m src.utils.test_summary
        }
        "2" { 
            # 詳細サマリーの表示
            python -m src.utils.test_summary --generate-reports
            python -m src.utils.test_summary --detailed
        }
        "3" {
            # フォルダ構造でレポート生成
            python -m src.utils.test_summary --generate-reports
            python -m src.utils.test_summary --folder
        }
        "4" {
            # 中間ファイルをクリーンアップ
            $confirm = Read-Host "中間ファイルを削除します。よろしいですか？ (Y/N)"
            if ($confirm -eq "Y" -or $confirm -eq "y") {
                python -m src.utils.test_summary --cleanup
                Write-Host "クリーンアップが完了しました" -ForegroundColor Green
            }
        }
        "5" {
            # 戻る
            return
        }
        default {
            Write-Host "無効な選択です。もう一度試してください。" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Read-Host "Enterキーを押してメニューに戻ります"
}

# テスト結果レポートをエクスポート
function Export-TestReport {
    Write-Host ""
    Write-Host "テスト結果レポートを生成しています..." -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "出力形式を選択してください:" -ForegroundColor Yellow
    Write-Host "1: テキスト形式 (TXT)"
    Write-Host "2: JSON形式"
    Write-Host "3: フォルダ形式（すべての形式）"
    Write-Host "4: HTML形式"
    Write-Host "5: 戻る"
    Write-Host ""
    
    $formatChoice = Read-Host "選択 (1-5)"
    
    switch ($formatChoice) {
        "1" {
            python -m src.utils.test_summary --format txt
        }
        "2" {
            python -m src.utils.test_summary --format json
        }
        "3" {
            python -m src.utils.test_summary --folder
        }
        "4" {
            Write-Host "HTMLレポートは通常のテスト実行時に '--html' オプションを指定して生成します。"
            Write-Host "既存のHTMLレポートをブラウザで表示しますか？ (Y/N)"
            $openHtml = Read-Host
            if ($openHtml -eq "Y" -or $openHtml -eq "y") {
                $htmlFiles = Get-ChildItem -Path "tests\results\html" -Filter "*_report_*.html" | Sort-Object LastWriteTime -Descending
                if ($htmlFiles.Count -gt 0) {
                    Start-Process $htmlFiles[0].FullName
                } else {
                    Write-Host "HTMLレポートが見つかりません。" -ForegroundColor Yellow
                }
            }
        }
        "5" {
            # 何もしない - メニューに戻る
        }
        default {
            Write-Host "無効な選択です。もう一度試してください。" -ForegroundColor Red
        }
    }
}

# 中間ファイルをクリーンアップ
function Cleanup-TestFiles {
    Write-Host ""
    Write-Host "中間ファイルをクリーンアップしています..." -ForegroundColor Cyan
    Write-Host ""
    
    $confirm = Read-Host "中間ファイルを削除します。よろしいですか？ (Y/N)"
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        python -m src.utils.test_summary --cleanup
        Write-Host "クリーンアップが完了しました" -ForegroundColor Green
    } else {
        Write-Host "クリーンアップを中止しました" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Read-Host "Enterキーを押してメニューに戻ります"
}

# メインループ
$running = $true
while ($running) {
    $selection = Show-Menu
    
    switch ($selection) {
        "1" { Invoke-AllTests }
        "2" { Invoke-AllTestsIncludingSkipped }
        "3" { Select-TestToRun }
        "4" { Show-TestSummary }
        "5" { Export-TestReport }
        "6" { Cleanup-TestFiles }
        "7" { 
            $running = $false
            Write-Host "プログラムを終了します..." -ForegroundColor Yellow
        }
        default {
            Write-Host "無効な選択です。1から7の数字を入力してください。" -ForegroundColor Red
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
