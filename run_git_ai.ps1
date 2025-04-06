# Git AI操作ツール
# PowerShell版 Git操作ツール（OpenAI API連携機能付き）

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# 変数の初期化
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$VENV_PATH = Join-Path $scriptDir 'venv'
$PYTHON_CMD = 'python'
$OPENAI_SCRIPT_PATH = Join-Path $scriptDir 'src\utils\openai_git_helper.py'
$GIT_BATCH_SCRIPT = Join-Path $scriptDir 'src\utils\git_batch.py'
$DEFAULT_REPO_PATH = '.'

# コマンドラインパラメータの初期化
$COMMAND = $null
$REPO_PATH = $DEFAULT_REPO_PATH
$PR_URL = $null
$FILE_PATH = $null
$FEATURE = $null
$TARGET_FILE = $null
$BRANCH = $null
$COMMIT_MESSAGE = $null
$USE_RECURSIVE = $null
$GITHUB_URL = $null
$DEPTH = 2

# コマンドライン引数の解析
$i = 0
while ($i -lt $args.Count) {
    # コマンド
    if ($args[$i] -eq "ai-commit") { $COMMAND = "ai-commit"; $i++ }
    elseif ($args[$i] -eq "analyze-pr") { $COMMAND = "analyze-pr"; $i++ }
    elseif ($args[$i] -eq "analyze-code") { $COMMAND = "analyze-code"; $i++ }
    elseif ($args[$i] -eq "suggest-implementation") { $COMMAND = "suggest-implementation"; $i++ }
    elseif ($args[$i] -eq "status") { $COMMAND = "status"; $i++ }
    elseif ($args[$i] -eq "pull") { $COMMAND = "pull"; $i++ }
    elseif ($args[$i] -eq "push") { $COMMAND = "push"; $i++ }
    elseif ($args[$i] -eq "commit") { $COMMAND = "commit"; $i++ }
    elseif ($args[$i] -eq "checkout") { $COMMAND = "checkout"; $i++ }
    elseif ($args[$i] -eq "reset") { $COMMAND = "reset"; $i++ }
    elseif ($args[$i] -eq "clean") { $COMMAND = "clean"; $i++ }
    elseif ($args[$i] -eq "check-sensitive-info") { $COMMAND = "check-sensitive-info"; $i++ }
    elseif ($args[$i] -eq "force-pull") { $COMMAND = "force-pull"; $i++ }
    elseif ($args[$i] -eq "full-push") { $COMMAND = "full-push"; $i++ }
    elseif ($args[$i] -eq "ai-full-push") { $COMMAND = "ai-full-push"; $i++ }
    elseif ($args[$i] -eq "git-init") { $COMMAND = "git-init"; $i++ }
    elseif ($args[$i] -eq "--help") { $COMMAND = "--help"; $i++ }
    # オプション
    elseif ($args[$i] -eq "--repo" -and $i+1 -lt $args.Count) { $REPO_PATH = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--branch" -and $i+1 -lt $args.Count) { $BRANCH = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--message" -and $i+1 -lt $args.Count) { $COMMIT_MESSAGE = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--pr-url" -and $i+1 -lt $args.Count) { $PR_URL = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--file" -and $i+1 -lt $args.Count) { $FILE_PATH = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--feature" -and $i+1 -lt $args.Count) { $FEATURE = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--target-file" -and $i+1 -lt $args.Count) { $TARGET_FILE = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--recursive") { $USE_RECURSIVE = "--recursive"; $i++ }
    elseif ($args[$i] -eq "--depth" -and $i+1 -lt $args.Count) { $DEPTH = $args[$i+1]; $i += 2 }
    elseif ($args[$i] -eq "--github-url" -and $i+1 -lt $args.Count) { $GITHUB_URL = $args[$i+1]; $i += 2 }
    else {
        Write-Host "警告: 不明なオプション '$($args[$i])' は無視されます" -ForegroundColor Yellow
        $i++
    }
}

# ヘルプ表示
function Show-Help {
    Write-Host "===== Git操作ツール with OpenAI API =====" -ForegroundColor Cyan
    Write-Host "使用法:"
    Write-Host "  .\run_git_ai.ps1 [コマンド] [オプション]"
    Write-Host ""
    Write-Host "コマンド:" -ForegroundColor Green
    Write-Host "  ai-commit             : 変更からコミットメッセージを生成してコミット"
    Write-Host "  analyze-pr            : プルリクエストを分析して要約"
    Write-Host "  analyze-code          : 指定されたファイルのコード品質を分析"
    Write-Host "  suggest-implementation: 新機能の実装提案"
    Write-Host "  status                : すべてのリポジトリのステータスを表示"
    Write-Host "  pull                  : すべてのリポジトリでプルを実行"
    Write-Host "  push                  : すべてのリポジトリでプッシュを実行"
    Write-Host "  commit                : すべてのリポジトリで変更をコミット"
    Write-Host "  checkout              : すべてのリポジトリで指定されたブランチをチェックアウト"
    Write-Host "  reset                 : すべてのリポジトリで変更をリセット"
    Write-Host "  clean                 : すべてのリポジトリで未追跡ファイルを削除"
    Write-Host "  check-sensitive-info  : プッシュ前に機密情報をチェック"
    Write-Host "  force-pull            : リモート状態に合わせて強制更新"
    Write-Host "  full-push             : 追加、コミット、プッシュを一度に実行"
    Write-Host "  ai-full-push          : 追加、AI生成メッセージでコミット、プッシュを実行"
    Write-Host "  git-init              : リポジトリの初期化、GitHub URLの設定、機密情報の確認、初期コミット"
    Write-Host ""
    Write-Host "オプション:" -ForegroundColor Yellow
    Write-Host "  --repo <dir>          : Gitリポジトリのパスを指定（デフォルト: カレントディレクトリ）"
    Write-Host "  --branch <name>       : ブランチ名を指定（checkout、pullコマンド用）"
    Write-Host "  --message <msg>       : コミットメッセージを指定"
    Write-Host "  --pr-url <url>        : 分析するプルリクエストのURL"
    Write-Host "  --file <path>         : 分析するファイルパス"
    Write-Host "  --feature <desc>      : 実装する機能の説明"
    Write-Host "  --target-file <file>  : 機能を実装するターゲットファイル名"
    Write-Host "  --recursive           : サブディレクトリを再帰的に検索（デフォルト: 無効）"
    Write-Host "  --depth <num>         : 再帰検索の最大深度（デフォルト: 2）"
    Write-Host "  --github-url <url>    : GitHubリポジトリURL（git-initコマンド用）"
    Write-Host "  --help                : このヘルプメッセージを表示"
    Write-Host ""
    Write-Host "例:" -ForegroundColor Cyan
    Write-Host "  .\run_git_ai.ps1 ai-commit"
    Write-Host "  .\run_git_ai.ps1 analyze-pr --pr-url https://github.com/user/repo/pull/123"
    Write-Host "  .\run_git_ai.ps1 analyze-code --file src/main.py"
    Write-Host "  .\run_git_ai.ps1 suggest-implementation --feature 'GitHub Issue要約の実装'"
    Write-Host "  .\run_git_ai.ps1 pull --branch main --recursive"
    Write-Host "  .\run_git_ai.ps1 commit --message '更新コミット'"
    Write-Host "  .\run_git_ai.ps1 git-init --github-url https://github.com/username/repo.git"
}

function Show-GitMenu {
    Clear-Host
    Write-Host '===== Git AI操作ツール =====' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '実行するGitコマンドを選択してください:' -ForegroundColor Cyan
    Write-Host '  [AI強化コマンド]' -ForegroundColor Magenta
    Write-Host '  1. AIによる自動コミット（コミットメッセージを自動生成）'
    Write-Host '  2. プルリクエスト分析'
    Write-Host '  3. コード品質分析'
    Write-Host '  4. 新機能実装の提案'
    Write-Host '  5. AI完全プッシュ（変更を追加、AIメッセージでコミット、プッシュ）'
    Write-Host '  [標準Gitコマンド]' -ForegroundColor Green
    Write-Host '  6. リポジトリステータス確認'
    Write-Host '  7. すべてのリポジトリをプル'
    Write-Host '  8. すべてのリポジトリをプッシュ'
    Write-Host '  9. すべてのリポジトリの変更をコミット'
    Write-Host '  10. すべてのリポジトリでブランチを切り替え'
    Write-Host '  11. すべてのリポジトリの変更をリセット'
    Write-Host '  12. すべてのリポジトリから未追跡ファイルを削除'
    Write-Host '  [セキュリティ/高度な操作]' -ForegroundColor Yellow
    Write-Host '  13. 機密情報のチェック（プッシュ前にAPIキーをチェック）'
    Write-Host '  14. 強制プル（リモート状態に合わせる）'
    Write-Host '  15. 完全プッシュ（追加、コミット、プッシュを一括操作）'
    Write-Host '  16. リポジトリ初期化と初回コミット'
    Write-Host ''
    Write-Host '  0. 終了' -ForegroundColor Red
    Write-Host ''
    
    $choice = Read-Host '選択（0-16）'
    
    switch ($choice) {
        '0' { Write-Host 'プログラムを終了します...' -ForegroundColor Yellow; exit 0 }
        '1' { return 'ai-commit' }
        '2' { return 'analyze-pr' }
        '3' { return 'analyze-code' }
        '4' { return 'suggest-implementation' }
        '5' { return 'ai-full-push' }
        '6' { return 'status' }
        '7' { return 'pull' }
        '8' { return 'push' }
        '9' { return 'commit' }
        '10' { return 'checkout' }
        '11' { return 'reset' }
        '12' { return 'clean' }
        '13' { return 'check-sensitive-info' }
        '14' { return 'force-pull' }
        '15' { return 'full-push' }
        '16' { return 'git-init' }
        default {
            Write-Host '無効な選択です。1～16の数字を入力してください。' -ForegroundColor Red
            Read-Host '続行するには何かキーを押してください'
            return $null
        }
    }
}

function Execute-GitCommand {
    param(
        [string]$command,
        [string]$repo_path = $REPO_PATH,
        [string]$pr_url = $PR_URL,
        [string]$file_path = $FILE_PATH,
        [string]$feature = $FEATURE,
        [string]$target_file = $TARGET_FILE,
        [string]$branch = $BRANCH,
        [string]$commit_message = $COMMIT_MESSAGE,
        [string]$use_recursive = $USE_RECURSIVE,
        [string]$github_url = $GITHUB_URL,
        [int]$depth = $DEPTH
    )
    
    # 必要なパラメータの確認
    if ($command -eq 'analyze-pr' -and [string]::IsNullOrEmpty($pr_url)) {
        $pr_url = Read-Host '分析するPR URLを入力してください'
        if ([string]::IsNullOrEmpty($pr_url)) {
            Write-Host 'エラー: PR URLは必須です。' -ForegroundColor Red
            return
        }
    }
    
    if ($command -eq 'analyze-code' -and [string]::IsNullOrEmpty($file_path)) {
        $file_path = Read-Host '分析するファイルパスを入力してください'
        if ([string]::IsNullOrEmpty($file_path)) {
            Write-Host 'エラー: ファイルパスは必須です。' -ForegroundColor Red
            return
        }
    }
    
    if ($command -eq 'suggest-implementation' -and [string]::IsNullOrEmpty($feature)) {
        $feature = Read-Host '実装する機能を説明してください'
        if ([string]::IsNullOrEmpty($feature)) {
            Write-Host 'エラー: 機能説明は必須です。' -ForegroundColor Red
            return
        }
    }

    if ($command -eq 'commit' -and [string]::IsNullOrEmpty($commit_message)) {
        $commit_message = Read-Host 'コミットメッセージを入力してください'
        if ([string]::IsNullOrEmpty($commit_message)) {
            Write-Host 'エラー: コミットメッセージは必須です。' -ForegroundColor Red
            return
        }
    }

    if ($command -eq 'checkout' -and [string]::IsNullOrEmpty($branch)) {
        $branch = Read-Host 'チェックアウトするブランチ名を入力してください'
        if ([string]::IsNullOrEmpty($branch)) {
            Write-Host 'エラー: ブランチ名は必須です。' -ForegroundColor Red
            return
        }
    }

    if ($command -eq 'git-init' -and [string]::IsNullOrEmpty($github_url)) {
        $github_url = Read-Host 'GitHubリポジトリURL（例: https://github.com/username/repo.git）を入力してください'
        if ([string]::IsNullOrEmpty($github_url)) {
            Write-Host 'エラー: GitHub URLは必須です。' -ForegroundColor Red
            return
        }
    }

    # 再帰検索の確認
    if ([string]::IsNullOrEmpty($use_recursive)) {
        $recursive_choice = Read-Host 'サブディレクトリを再帰的に検索しますか？ (Y/N)'
        if ($recursive_choice -eq 'Y' -or $recursive_choice -eq 'y') {
            $use_recursive = '--recursive'
        }
    }
    
    # Pythonが利用可能か確認
    try {
        & $PYTHON_CMD --version | Out-Null
    } catch {
        Write-Host 'エラー: Pythonがインストールされていないか、PATHに設定されていません。' -ForegroundColor Red
        Read-Host '続行するには何かキーを押してください'
        return
    }
    
    # 仮想環境のアクティベート
    if (Test-Path $(Join-Path $VENV_PATH 'Scripts\Activate.ps1')) {
        Write-Host '仮想環境をアクティベートしています...' -ForegroundColor Green
        & $(Join-Path $VENV_PATH 'Scripts\Activate.ps1')
        
        # PYTHONPATHを設定してプロジェクトルートを参照できるようにする
        $env:PYTHONPATH = $scriptDir
    } else {
        Write-Host '仮想環境が見つかりません。システムのPythonを使用します。' -ForegroundColor Yellow
    }
    
    # git-initコマンドの特別な処理
    if ($command -eq 'git-init') {
        Write-Host '[処理] リポジトリの初期化と設定を行っています...' -ForegroundColor Cyan
        
        Write-Host 'Gitリポジトリを初期化しています...'
        git -c credential.helper="" -c core.editor=notepad -c core.autocrlf=true init
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'エラー: リポジトリの初期化に失敗しました。' -ForegroundColor Red
            return
        }
        
        Write-Host "リモートリポジトリを設定しています: $github_url"
        git -c credential.helper="" remote add origin $github_url
        if ($LASTEXITCODE -ne 0) {
            Write-Host '警告: リモートオリジンの追加に失敗しました。URLの更新を試みます...' -ForegroundColor Yellow
            git -c credential.helper="" remote set-url origin $github_url
        }
        
        Write-Host '初期コミットを作成しています...'
        git add .
        git -c credential.helper="" commit -m "Initial commit"
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'エラー: コミットに失敗しました。' -ForegroundColor Red
            return
        }
        
        Write-Host 'masterブランチにプッシュしています...'
        git -c credential.helper="" push -u origin master
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'エラー: プッシュに失敗しました。' -ForegroundColor Red
            return
        }
        
        Write-Host 'リポジトリの初期化と初期コミットが完了しました。' -ForegroundColor Green
        Write-Host "リモートリポジトリURL: $github_url" -ForegroundColor Green
        return
    }
    
    # 必要なスクリプトの存在確認
    if ($command -in 'ai-commit', 'analyze-pr', 'analyze-code', 'suggest-implementation', 'check-sensitive-info', 'force-pull', 'full-push', 'ai-full-push') {
        if (-not (Test-Path $OPENAI_SCRIPT_PATH)) {
            Write-Host "エラー: OpenAI Gitヘルパースクリプトが見つかりません: $OPENAI_SCRIPT_PATH" -ForegroundColor Red
            return
        }
    } else {
        if (-not (Test-Path $GIT_BATCH_SCRIPT)) {
            Write-Host "エラー: Gitバッチ処理スクリプトが見つかりません: $GIT_BATCH_SCRIPT" -ForegroundColor Red
            return
        }
    }
    
    # コマンドの実行
    switch ($command) {
        'ai-commit' {
            Write-Host 'AIによるコミットを実行しています...' -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH ai-commit --repo $repo_path
        }
        'analyze-pr' {
            Write-Host "[処理] プルリクエスト $pr_url を分析中..." -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH analyze-pr --repo $repo_path --pr-url $pr_url
        }
        'analyze-code' {
            Write-Host "[処理] ファイル $file_path を分析中..." -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH analyze-code --repo $repo_path --file $file_path
        }
        'suggest-implementation' {
            Write-Host "[処理] '$feature' の実装を提案中..." -ForegroundColor Cyan
            if (-not [string]::IsNullOrEmpty($target_file)) {
                & $PYTHON_CMD $OPENAI_SCRIPT_PATH suggest-implementation --repo $repo_path --feature $feature --target-file $target_file
            } else {
                & $PYTHON_CMD $OPENAI_SCRIPT_PATH suggest-implementation --repo $repo_path --feature $feature
            }
        }
        'check-sensitive-info' {
            Write-Host '[処理] プッシュ前に機密情報をチェックしています...' -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH check-sensitive-info --repo $repo_path
        }
        'force-pull' {
            Write-Host '[処理] リモート状態に強制的に更新しています...' -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH force-pull --repo $repo_path
        }
        'full-push' {
            Write-Host '[処理] 追加、コミット、プッシュを一括実行しています...' -ForegroundColor Cyan
            & $PYTHON_CMD $OPENAI_SCRIPT_PATH full-push --repo $repo_path
        }
        'ai-full-push' {
            Write-Host 'AIアシスト付きフルプッシュを実行しています...' -ForegroundColor Cyan
            if (-not [string]::IsNullOrEmpty($branch)) {
                & $PYTHON_CMD $OPENAI_SCRIPT_PATH ai-full-push --repo $repo_path --branch $branch
            } else {
                & $PYTHON_CMD $OPENAI_SCRIPT_PATH ai-full-push --repo $repo_path
            }
        }
        default {
            # 標準Gitコマンド用
            $python_args = "$GIT_BATCH_SCRIPT $command --path $repo_path --depth $depth $use_recursive"
            
            if (-not [string]::IsNullOrEmpty($branch)) {
                $python_args += " --branch $branch"
            }
            
            if (-not [string]::IsNullOrEmpty($commit_message)) {
                $python_args += " --message '$commit_message'"
            }
            
            Write-Host ""
            Write-Host "==========================================================="
            Write-Host "Git操作ツール - コマンド: $command" -ForegroundColor Cyan
            Write-Host "対象リポジトリ: $repo_path"
            if (-not [string]::IsNullOrEmpty($pr_url)) { Write-Host "PR URL: $pr_url" }
            if (-not [string]::IsNullOrEmpty($file_path)) { Write-Host "対象ファイル: $file_path" }
            if (-not [string]::IsNullOrEmpty($feature)) { Write-Host "機能説明: $feature" }
            if (-not [string]::IsNullOrEmpty($target_file)) { Write-Host "対象ファイル: $target_file" }
            if (-not [string]::IsNullOrEmpty($branch)) { Write-Host "ブランチ: $branch" }
            if (-not [string]::IsNullOrEmpty($commit_message)) { Write-Host "コミットメッセージ: $commit_message" }
            if (-not [string]::IsNullOrEmpty($github_url)) { Write-Host "GitHub URL: $github_url" }
            if ($use_recursive -eq '--recursive') { Write-Host "再帰検索: 有効（最大深度: $depth）" }
            Write-Host "==========================================================="
            Write-Host ""
            
            Write-Host '[INFO] Pythonスクリプトを実行しています...' -ForegroundColor Green
            Invoke-Expression "$PYTHON_CMD $python_args"
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host '[ERROR] 処理中にエラーが発生しました。' -ForegroundColor Red
            } else {
                Write-Host '[INFO] 処理が正常に完了しました。' -ForegroundColor Green
            }
        }
    }
    
    # 仮想環境の非アクティベート
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
    }
    
    Write-Host ''
    Read-Host '続行するには何かキーを押してください'
}

# メイン処理
# ヘルプモードなら説明を表示して終了
if ($COMMAND -eq "--help") {
    Show-Help
    exit 0
}

# コマンドがない場合はメニューを表示
if ([string]::IsNullOrEmpty($COMMAND)) {
    Write-Host "===== Git AIツール - PowerShell版 ====="
    Write-Host ""
    
    while ($true) {
        $command = Show-GitMenu
        if (-not [string]::IsNullOrEmpty($command)) {
            Execute-GitCommand -command $command
        }
    }
} else {
    # コマンドが指定されていれば直接実行
    Execute-GitCommand -command $COMMAND
}
