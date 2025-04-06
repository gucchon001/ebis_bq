@echo off
setlocal enabledelayedexpansion
rem Windows環境での文字化け対策 - 文字コードをUTF-8に設定
chcp 65001 >nul

rem ===== OpenAI APIを利用したGit操作ツール =====
rem GitコマンドをAIで強化する機能を提供します。

rem 初期化
set "VENV_PATH=.\venv"
set "PYTHON_CMD=python"
set "OPENAI_SCRIPT_PATH=src\utils\openai_git_helper.py"
set "GIT_BATCH_SCRIPT=src\utils\git_batch.py"
set "DEFAULT_REPO_PATH=."
set "REPO_PATH=%DEFAULT_REPO_PATH%"
set "COMMAND="
set "PR_URL="
set "FILE_PATH="
set "FEATURE="
set "TARGET_FILE="
set "BRANCH="
set "COMMIT_MESSAGE="
set "USE_RECURSIVE="
set "DEPTH=2"

rem GitHubデスクトップが自動起動しないようにする環境変数設定
set "GIT_OPTIONAL_LOCKS=0"
set "EDITOR=notepad"
set "GIT_EDITOR=notepad"
set "GIT_TERMINAL_PROMPT=1"
set "GIT_CREDENTIAL_HELPER="

rem コマンドライン引数の最初の引数をコマンドとして設定
if "%~1" NEQ "" (
    set "COMMAND=%~1"
    shift
)

rem ヘルプ表示
if "%COMMAND%"=="--help" (
    echo ===== OpenAI APIを利用したGit操作ツール =====
    echo 使用方法:
    echo   run_git_ai.bat [コマンド] [オプション]
    echo.
    echo コマンド:
    echo   ai-commit             : 変更内容からコミットメッセージを自動生成してコミット
    echo   analyze-pr            : プルリクエストを分析して要約
    echo   analyze-code          : 指定されたファイルのコード品質を分析
    echo   suggest-implementation: 新機能の実装案を提案
    echo   status                : 全リポジトリの状態を表示
    echo   pull                  : 全リポジトリのpullを実行
    echo   push                  : 全リポジトリのpushを実行
    echo   commit                : 全リポジトリの変更をコミット
    echo   checkout              : 全リポジトリで指定ブランチにチェックアウト
    echo   reset                 : 全リポジトリの変更をリセット
    echo   clean                 : 全リポジトリの追跡されていないファイルを削除
    echo   check-sensitive-info  : 機密情報のチェック (プッシュ前にAPIキーなどをチェック)
    echo   force-pull            : リモートの最新状態に強制的に合わせる
    echo   full-push             : 変更をadd、commit、pushまで一気に実行
    echo   ai-full-push          : 変更をadd、AI生成メッセージでcommit、pushまで一気に実行
    echo   git-init              : リポジトリ初期化、GitHub URL設定、機密情報チェック、初期コミットまで実行
    echo.
    echo オプション:
    echo   --repo ^<dir^>         : Gitリポジトリのパスを指定 (デフォルト: カレントディレクトリ)
    echo   --branch ^<name^>      : ブランチ名を指定 (checkout, pullコマンド用)
    echo   --message ^<msg^>      : コミットメッセージを指定
    echo   --pr-url ^<url^>       : 分析するプルリクエストのURL
    echo   --file ^<path^>        : 分析対象のファイルパス
    echo   --feature ^<desc^>     : 実装する機能の説明
    echo   --target-file ^<file^> : 機能を実装するターゲットファイル名
    echo   --recursive           : サブディレクトリも再帰的に検索 (デフォルト: 無効)
    echo   --depth ^<num^>        : 再帰検索時の最大深度 (デフォルト: 2)
    echo   --help                : このヘルプメッセージを表示
    echo.
    echo 例:
    echo   run_git_ai.bat ai-commit
    echo   run_git_ai.bat analyze-pr --pr-url https://github.com/user/repo/pull/123
    echo   run_git_ai.bat analyze-code --file src/main.py
    echo   run_git_ai.bat suggest-implementation --feature "GitHubのIssueを自動で要約する機能"
    echo   run_git_ai.bat pull --branch main --recursive
    echo   run_git_ai.bat commit --message "変更コミット"
    goto END
)

rem コマンドライン引数の解析
:parse_args
if "%~1"=="" goto setup_environment

rem コマンド
if "%~1"=="ai-commit" (
    set "COMMAND=ai-commit"
    shift
    goto parse_args
)
if "%~1"=="analyze-pr" (
    set "COMMAND=analyze-pr"
    shift
    goto parse_args
)
if "%~1"=="analyze-code" (
    set "COMMAND=analyze-code"
    shift
    goto parse_args
)
if "%~1"=="suggest-implementation" (
    set "COMMAND=suggest-implementation"
    shift
    goto parse_args
)
if "%~1"=="status" (
    set "COMMAND=status"
    shift
    goto parse_args
)
if "%~1"=="pull" (
    set "COMMAND=pull"
    shift
    goto parse_args
)
if "%~1"=="push" (
    set "COMMAND=push"
    shift
    goto parse_args
)
if "%~1"=="commit" (
    set "COMMAND=commit"
    shift
    goto parse_args
)
if "%~1"=="checkout" (
    set "COMMAND=checkout"
    shift
    goto parse_args
)
if "%~1"=="reset" (
    set "COMMAND=reset"
    shift
    goto parse_args
)
if "%~1"=="clean" (
    set "COMMAND=clean"
    shift
    goto parse_args
)
if "%~1"=="check-sensitive-info" (
    set "COMMAND=check-sensitive-info"
    shift
    goto parse_args
)
if "%~1"=="force-pull" (
    set "COMMAND=force-pull"
    shift
    goto parse_args
)
if "%~1"=="full-push" (
    set "COMMAND=full-push"
    shift
    goto parse_args
)
if "%~1"=="ai-full-push" (
    set "COMMAND=ai-full-push"
    shift
    goto parse_args
)
if "%~1"=="git-init" (
    set "COMMAND=git-init"
    shift
    goto parse_args
)

rem オプション
if "%~1"=="--repo" (
    set "REPO_PATH=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--branch" (
    set "BRANCH=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--message" (
    set "COMMIT_MESSAGE=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--pr-url" (
    set "PR_URL=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--file" (
    set "FILE_PATH=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--feature" (
    set "FEATURE=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--target-file" (
    set "TARGET_FILE=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--recursive" (
    set "USE_RECURSIVE=--recursive"
    shift
    goto parse_args
)
if "%~1"=="--depth" (
    set "DEPTH=%~2"
    shift
    shift
    goto parse_args
)

echo 警告: 不明なオプション "%~1" は無視されます
shift
goto parse_args

:setup_environment
rem コマンドが指定されていない場合はメニューを表示
if "%COMMAND%"=="" (
    echo 実行するGitコマンドを選択してください:
    echo   [AI強化コマンド]
    echo   1. AI自動コミット ^(コミットメッセージを自動生成^)
    echo   2. プルリクエスト分析
    echo   3. コード品質分析
    echo   4. 新機能の実装提案
    echo   5. AI全処理プッシュ ^(変更のadd、AI生成メッセージでcommit、push^)
    echo   [標準Gitコマンド]
    echo   6. リポジトリのステータス確認
    echo   7. 全リポジトリをプル
    echo   8. 全リポジトリをプッシュ
    echo   9. 全リポジトリの変更をコミット
    echo   10. 全リポジトリのブランチを切り替え
    echo   11. 全リポジトリの変更をリセット
    echo   12. 全リポジトリの追跡されていないファイルを削除
    echo   [セキュリティ/高度な操作]
    echo   13. 機密情報のチェック ^(プッシュ前にAPIキーなどをチェック^)
    echo   14. リモートの最新状態に強制的に合わせる ^(force-pull^)
    echo   15. 変更をadd、commit、pushまで一気に実行 ^(full-push^)
    echo   16. リポジトリ初期化と初期コミット ^(git-init^)
    
    set /p "MENU_CHOICE=選択肢を入力してください (1-16): "
    
    if "%MENU_CHOICE%"=="1" set "COMMAND=ai-commit"
    if "%MENU_CHOICE%"=="2" set "COMMAND=analyze-pr"
    if "%MENU_CHOICE%"=="3" set "COMMAND=analyze-code"
    if "%MENU_CHOICE%"=="4" set "COMMAND=suggest-implementation"
    if "%MENU_CHOICE%"=="5" set "COMMAND=ai-full-push"
    if "%MENU_CHOICE%"=="6" set "COMMAND=status"
    if "%MENU_CHOICE%"=="7" set "COMMAND=pull"
    if "%MENU_CHOICE%"=="8" set "COMMAND=push"
    if "%MENU_CHOICE%"=="9" set "COMMAND=commit"
    if "%MENU_CHOICE%"=="10" set "COMMAND=checkout"
    if "%MENU_CHOICE%"=="11" set "COMMAND=reset"
    if "%MENU_CHOICE%"=="12" set "COMMAND=clean"
    if "%MENU_CHOICE%"=="13" set "COMMAND=check-sensitive-info"
    if "%MENU_CHOICE%"=="14" set "COMMAND=force-pull"
    if "%MENU_CHOICE%"=="15" set "COMMAND=full-push"
    if "%MENU_CHOICE%"=="16" set "COMMAND=git-init"
    
    if not defined COMMAND (
        echo エラー: 無効な選択肢です。1-16の数字を入力してください。
        pause
        exit /b 1
    )
)

rem 必要なパラメータの追加入力を促す
if "%COMMAND%"=="analyze-pr" if "%PR_URL%"=="" (
    set /p "PR_URL=分析するPR URLを入力してください: "
    if "!PR_URL!"=="" (
        echo エラー: PR URLは必須です。
        exit /b 1
    )
)

if "%COMMAND%"=="analyze-code" if "%FILE_PATH%"=="" (
    set /p "FILE_PATH=分析するファイルパスを入力してください: "
    if "!FILE_PATH!"=="" (
        echo エラー: ファイルパスは必須です。
        exit /b 1
    )
)

if "%COMMAND%"=="suggest-implementation" if "%FEATURE%"=="" (
    set /p "FEATURE=実装する機能を説明してください: "
    if "!FEATURE!"=="" (
        echo エラー: 機能の説明は必須です。
        exit /b 1
    )
)

if "%COMMAND%"=="commit" if "%COMMIT_MESSAGE%"=="" (
    set /p "COMMIT_MESSAGE=コミットメッセージを入力してください: "
    if "!COMMIT_MESSAGE!"=="" (
        echo エラー: コミットメッセージは必須です。
        exit /b 1
    )
)

if "%COMMAND%"=="checkout" if "%BRANCH%"=="" (
    set /p "BRANCH=切り替え先のブランチ名を入力してください: "
    if "!BRANCH!"=="" (
        echo エラー: ブランチ名は必須です。
        exit /b 1
    )
)

rem 再帰検索の確認
if not defined USE_RECURSIVE (
    set /p "RECURSIVE_CHOICE=サブディレクトリも再帰的に検索しますか？ (Y/N): "
    if /i "!RECURSIVE_CHOICE!"=="Y" set "USE_RECURSIVE=--recursive"
)

rem Pythonが利用可能か確認
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Python がインストールされていないか、環境パスが設定されていません。
    pause
    exit /b 1
)

rem 仮想環境の存在確認と有効化
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] 仮想環境をアクティブ化しています...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [INFO] 仮想環境が見つかりません。システムのPythonを使用します。
)

rem 必要なスクリプトの存在確認
if "%COMMAND%"=="ai-commit" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo エラー: OpenAI Git操作スクリプトが見つかりません: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="analyze-pr" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo エラー: OpenAI Git操作スクリプトが見つかりません: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="analyze-code" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo エラー: OpenAI Git操作スクリプトが見つかりません: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="suggest-implementation" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo エラー: OpenAI Git操作スクリプトが見つかりません: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else (
    if not exist "%GIT_BATCH_SCRIPT%" (
        echo エラー: Git一括処理スクリプトが見つかりません: %GIT_BATCH_SCRIPT%
        goto END
    )
)

rem コマンドの構築と実行
if "%COMMAND%"=="ai-commit" (
    echo AI支援コミットを実行中...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-commit --repo "%REPO_PATH%"
    if !ERRORLEVEL! neq 0 (
        echo エラー: AI支援コミットの実行中にエラーが発生しました。
        set /a ERROR_COUNT+=1
    )
)

if "%COMMAND%"=="analyze-pr" (
    if not defined PR_URL (
        set /p "PR_URL=分析するプルリクエストのURLを入力してください: "
    )
    echo [処理] プルリクエスト %PR_URL% を分析します...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" analyze-pr --repo "%REPO_PATH%" --pr-url "%PR_URL%"
    goto END
)

if "%COMMAND%"=="analyze-code" (
    if not defined FILE_PATH (
        set /p "FILE_PATH=分析するファイルパスを入力してください: "
    )
    echo [処理] ファイル %FILE_PATH% を分析します...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" analyze-code --repo "%REPO_PATH%" --file "%FILE_PATH%"
    goto END
)

if "%COMMAND%"=="suggest-implementation" (
    if not defined FEATURE (
        set /p "FEATURE=実装する機能を説明してください: "
    )
    echo [処理] 機能 "%FEATURE%" の実装案を提案します...
    if defined TARGET_FILE (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" suggest-implementation --repo "%REPO_PATH%" --feature "%FEATURE%" --target-file "%TARGET_FILE%"
    ) else (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" suggest-implementation --repo "%REPO_PATH%" --feature "%FEATURE%"
    )
    goto END
)

if "%COMMAND%"=="check-sensitive-info" (
    echo [処理] プッシュ前の機密情報チェックを実行します...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" check-sensitive-info --repo "%REPO_PATH%"
    
    if errorlevel 1 (
        echo [警告] 機密情報が検出されました。プッシュする前に確認してください。
        pause
    )
    
    goto END
)

if "%COMMAND%"=="force-pull" (
    echo [処理] リモートの最新状態に強制的に合わせます...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" force-pull --repo "%REPO_PATH%"
    goto END
)

if "%COMMAND%"=="full-push" (
    echo [処理] 変更をadd、commit、pushまで一気に実行します...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" full-push --repo "%REPO_PATH%"
    goto END
)

if "%COMMAND%"=="ai-full-push" (
    echo AI支援全処理プッシュを実行中...
    if defined BRANCH (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-full-push --repo "%REPO_PATH%" --branch "%BRANCH%"
    ) else (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-full-push --repo "%REPO_PATH%"
    )
    if !ERRORLEVEL! neq 0 (
        echo エラー: AI支援全処理プッシュの実行中にエラーが発生しました。
        set /a ERROR_COUNT+=1
    )
)

if "%COMMAND%"=="git-init" (
    echo リポジトリの初期化と設定を行います...
    
    rem 1. git initで初期化
    echo Gitリポジトリを初期化しています...
    git -c credential.helper="" -c core.editor=notepad -c core.autocrlf=true init
    if !ERRORLEVEL! neq 0 (
        echo エラー: リポジトリの初期化に失敗しました。
        goto END
    )
    
    rem 2. GitHub URLの入力プロンプト
    set /p "GITHUB_URL=GitHub リポジトリURLを入力してください (例: https://github.com/username/repo.git): "
    if "!GITHUB_URL!"=="" (
        echo エラー: GitHub URLは必須です。
        goto END
    )
    
    rem 3. リモートリポジトリの設定
    echo リモートリポジトリを設定しています...
    git -c credential.helper="" remote add origin !GITHUB_URL!
    if !ERRORLEVEL! neq 0 (
        echo エラー: リモートリポジトリの設定に失敗しました。
        goto END
    )
    
    rem 4. 初期コミットとプッシュ
    echo 初期コミットを実行しています...
    git add .
    git -c credential.helper="" commit -m "Initial commit"
    
    echo プッシュを実行しています...
    git -c credential.helper="" push -u origin main
    
    if !ERRORLEVEL! neq 0 (
        echo エラー: 初期コミットとプッシュに失敗しました。
        goto END
    )
    
    echo リポジトリの初期化と初期コミットが完了しました。
    echo リモートリポジトリURL: !GITHUB_URL!
    goto END
)

rem 標準Gitコマンドの場合
set "PYTHON_ARGS=%GIT_BATCH_SCRIPT% %COMMAND% --path %REPO_PATH% --depth %DEPTH% %USE_RECURSIVE%"

if not "%BRANCH%"=="" (
    set "PYTHON_ARGS=%PYTHON_ARGS% --branch %BRANCH%"
)

if not "%COMMIT_MESSAGE%"=="" (
    set "PYTHON_ARGS=%PYTHON_ARGS% --message "%COMMIT_MESSAGE%""
)

echo.
echo ===========================================================
echo Git操作ツール - コマンド: %COMMAND%
echo 対象リポジトリ: %REPO_PATH%
if not "%PR_URL%"=="" echo PR URL: %PR_URL%
if not "%FILE_PATH%"=="" echo 対象ファイル: %FILE_PATH%
if not "%FEATURE%"=="" echo 機能説明: %FEATURE%
if not "%TARGET_FILE%"=="" echo ターゲットファイル: %TARGET_FILE%
if not "%BRANCH%"=="" echo ブランチ: %BRANCH%
if not "%COMMIT_MESSAGE%"=="" echo コミットメッセージ: %COMMIT_MESSAGE%
if "%USE_RECURSIVE%"=="--recursive" echo 再帰検索: 有効 (最大深度: %DEPTH%)
echo ===========================================================
echo.

echo [INFO] Pythonスクリプトを実行しています...
%PYTHON_CMD% %PYTHON_ARGS%

if errorlevel 1 (
    echo [ERROR] 処理中にエラーが発生しました。
) else (
    echo [INFO] 処理が正常に完了しました。
)

rem 仮想環境の非アクティブ化
if exist "%VENV_PATH%\Scripts\deactivate.bat" (
    call "%VENV_PATH%\Scripts\deactivate.bat"
)

:END
echo.
pause
endlocal 