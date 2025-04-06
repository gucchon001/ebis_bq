@echo off
chcp 65001 >nul
setlocal

echo ===== Git AIツール - PowerShell版 =====
echo.

rem PowerShellスクリプトを実行
powershell -ExecutionPolicy Bypass -NoProfile -Command ^
"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ^
[Console]::InputEncoding = [System.Text.Encoding]::UTF8; ^
& {param($scriptDir) ^
$VENV_PATH = Join-Path $scriptDir 'venv'; ^
$PYTHON_CMD = 'python'; ^
$OPENAI_SCRIPT_PATH = Join-Path $scriptDir 'src\utils\openai_git_helper.py'; ^
$GIT_BATCH_SCRIPT = Join-Path $scriptDir 'src\utils\git_batch.py'; ^
$DEFAULT_REPO_PATH = '.'; ^
^
function Show-GitMenu { ^
    Clear-Host; ^
    Write-Host '===== Git AI操作ツール =====' -ForegroundColor Cyan; ^
    Write-Host ''; ^
    Write-Host '実行するGitコマンドを選択してください:' -ForegroundColor Cyan; ^
    Write-Host '  [AI強化コマンド]' -ForegroundColor Magenta; ^
    Write-Host '  1. AIによる自動コミット（コミットメッセージを自動生成）'; ^
    Write-Host '  2. プルリクエスト分析'; ^
    Write-Host '  3. コード品質分析'; ^
    Write-Host '  4. 新機能実装の提案'; ^
    Write-Host '  5. AI完全プッシュ（変更を追加、AIメッセージでコミット、プッシュ）'; ^
    Write-Host '  [標準Gitコマンド]' -ForegroundColor Green; ^
    Write-Host '  6. リポジトリステータス確認'; ^
    Write-Host '  7. すべてのリポジトリをプル'; ^
    Write-Host '  8. すべてのリポジトリをプッシュ'; ^
    Write-Host '  9. すべてのリポジトリの変更をコミット'; ^
    Write-Host '  10. すべてのリポジトリでブランチを切り替え'; ^
    Write-Host '  11. すべてのリポジトリの変更をリセット'; ^
    Write-Host '  12. すべてのリポジトリから未追跡ファイルを削除'; ^
    Write-Host '  [セキュリティ/高度な操作]' -ForegroundColor Yellow; ^
    Write-Host '  13. 機密情報のチェック（プッシュ前にAPIキーをチェック）'; ^
    Write-Host '  14. 強制プル（リモート状態に合わせる）'; ^
    Write-Host '  15. 完全プッシュ（追加、コミット、プッシュを一括操作）'; ^
    Write-Host '  16. リポジトリ初期化と初回コミット'; ^
    Write-Host ''; ^
    Write-Host '  0. 終了' -ForegroundColor Red; ^
    Write-Host ''; ^
    ^
    $choice = Read-Host '選択（0-16）'; ^
    ^
    switch ($choice) { ^
        '0' { Write-Host 'プログラムを終了します...' -ForegroundColor Yellow; exit 0; } ^
        '1' { return 'ai-commit'; } ^
        '2' { return 'analyze-pr'; } ^
        '3' { return 'analyze-code'; } ^
        '4' { return 'suggest-implementation'; } ^
        '5' { return 'ai-full-push'; } ^
        '6' { return 'status'; } ^
        '7' { return 'pull'; } ^
        '8' { return 'push'; } ^
        '9' { return 'commit'; } ^
        '10' { return 'checkout'; } ^
        '11' { return 'reset'; } ^
        '12' { return 'clean'; } ^
        '13' { return 'check-sensitive-info'; } ^
        '14' { return 'force-pull'; } ^
        '15' { return 'full-push'; } ^
        '16' { return 'git-init'; } ^
        default { ^
            Write-Host '無効な選択です。1～16の数字を入力してください。' -ForegroundColor Red; ^
            Read-Host '続行するには何かキーを押してください'; ^
            return $null; ^
        } ^
    } ^
} ^
^
function Execute-GitCommand { ^
    param($command) ^
    ^
    $REPO_PATH = $DEFAULT_REPO_PATH; ^
    $PR_URL = $null; ^
    $FILE_PATH = $null; ^
    $FEATURE = $null; ^
    $TARGET_FILE = $null; ^
    $BRANCH = $null; ^
    $COMMIT_MESSAGE = $null; ^
    $USE_RECURSIVE = $null; ^
    $GITHUB_URL = $null; ^
    $DEPTH = 2; ^
    ^
    # 仮想環境のアクティベート ^
    if (Test-Path $(Join-Path $VENV_PATH 'Scripts\Activate.ps1')) { ^
        Write-Host '仮想環境をアクティベートしています...' -ForegroundColor Green; ^
        & $(Join-Path $VENV_PATH 'Scripts\Activate.ps1'); ^
    } else { ^
        Write-Host '仮想環境が見つかりません: ' $VENV_PATH -ForegroundColor Yellow; ^
    } ^
    ^
    switch ($command) { ^
        'ai-commit' { ^
            Write-Host 'AIによるコミットを実行しています...' -ForegroundColor Cyan; ^
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH ai-commit --repo $REPO_PATH; ^
        } ^
        'analyze-pr' { ^
            $PR_URL = Read-Host '分析するPR URLを入力してください'; ^
            Write-Host '[処理] プルリクエスト '$PR_URL' を分析中...' -ForegroundColor Cyan; ^
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH analyze-pr --repo $REPO_PATH --pr-url $PR_URL; ^
        } ^
        'analyze-code' { ^
            $FILE_PATH = Read-Host '分析するファイルパスを入力してください'; ^
            Write-Host '[処理] ファイル '$FILE_PATH' を分析中...' -ForegroundColor Cyan; ^
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH analyze-code --repo $REPO_PATH --file $FILE_PATH; ^
        } ^
        'force-pull' { ^
            Write-Host '[処理] リモート状態に強制的に更新しています...' -ForegroundColor Cyan; ^
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH force-pull --repo $REPO_PATH; ^
        } ^
        'pull' { ^
            & $PYTHON_CMD $GIT_BATCH_SCRIPT pull --path $REPO_PATH; ^
        } ^
        'push' { ^
            & $PYTHON_CMD $GIT_BATCH_SCRIPT push --path $REPO_PATH; ^
        } ^
        'status' { ^
            & $PYTHON_CMD $GIT_BATCH_SCRIPT status --path $REPO_PATH; ^
        } ^
        default { ^
            Write-Host 'この機能は現在実装中です: '$command -ForegroundColor Yellow; ^
        } ^
    } ^
    ^
    # 仮想環境の非アクティベート ^
    if (Get-Command deactivate -ErrorAction SilentlyContinue) { ^
        deactivate; ^
    } ^
    ^
    Write-Host ''; ^
    Read-Host '続行するには何かキーを押してください'; ^
} ^
^
# メインループ ^
while ($true) { ^
    $command = Show-GitMenu; ^
    if ($command) { ^
        Execute-GitCommand $command; ^
    } ^
} ^
} '%~dp0'"

endlocal 