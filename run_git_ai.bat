@echo off
rem 文字化け対策 (UTF-8)
chcp 65001 >nul
setlocal enabledelayedexpansion

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
set "GITHUB_URL="

rem GitHubデスクトップが自動起動しないようにする環境変数設定
set "GIT_OPTIONAL_LOCKS=0"
set "EDITOR=notepad"
set "GIT_EDITOR=notepad"
set "GIT_TERMINAL_PROMPT=1"
set "GIT_CREDENTIAL_HELPER="

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
if "%~1"=="--help" (
    set "COMMAND=--help"
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
if "%~1"=="--github-url" (
    set "GITHUB_URL=%~2"
    shift
    shift
    goto parse_args
)

echo Warning: Unknown option "%~1" will be ignored
shift
goto parse_args

:setup_environment
rem ヘルプ表示
if "%COMMAND%"=="--help" (
    echo ===== Git Operations Tool with OpenAI API =====
    echo Usage:
    echo   run_git_ai.bat [command] [options]
    echo.
    echo Commands:
    echo   ai-commit             : Generate commit message from changes and commit
    echo   analyze-pr            : Analyze and summarize a pull request
    echo   analyze-code          : Analyze code quality of specified file
    echo   suggest-implementation: Suggest implementation for a new feature
    echo   status                : Show status of all repositories
    echo   pull                  : Execute pull on all repositories
    echo   push                  : Execute push on all repositories
    echo   commit                : Commit changes in all repositories
    echo   checkout              : Checkout specified branch in all repositories
    echo   reset                 : Reset changes in all repositories
    echo   clean                 : Remove untracked files in all repositories
    echo   check-sensitive-info  : Check for sensitive information before pushing
    echo   force-pull            : Force update to match remote state
    echo   full-push             : Execute add, commit, and push in one go
    echo   ai-full-push          : Execute add, commit with AI-generated message, and push
    echo   git-init              : Initialize repository, set GitHub URL, check sensitive info, initial commit
    echo.
    echo Options:
    echo   --repo ^<dir^>         : Specify Git repository path (default: current directory)
    echo   --branch ^<name^>      : Specify branch name (for checkout, pull commands)
    echo   --message ^<msg^>      : Specify commit message
    echo   --pr-url ^<url^>       : URL of the pull request to analyze
    echo   --file ^<path^>        : File path to analyze
    echo   --feature ^<desc^>     : Description of feature to implement
    echo   --target-file ^<file^> : Target file name to implement feature
    echo   --recursive           : Search subdirectories recursively (default: disabled)
    echo   --depth ^<num^>        : Maximum depth for recursive search (default: 2)
    echo   --github-url ^<url^>   : GitHub repository URL (for git-init command)
    echo   --help                : Display this help message
    echo.
    echo Examples:
    echo   run_git_ai.bat ai-commit
    echo   run_git_ai.bat analyze-pr --pr-url https://github.com/user/repo/pull/123
    echo   run_git_ai.bat analyze-code --file src/main.py
    echo   run_git_ai.bat suggest-implementation --feature "Implement GitHub Issue summarization"
    echo   run_git_ai.bat pull --branch main --recursive
    echo   run_git_ai.bat commit --message "Update commit"
    echo   run_git_ai.bat git-init --github-url https://github.com/username/repo.git
    goto END
)

rem コマンドが指定されていない場合はメニューを表示
if "%COMMAND%"=="" (
    echo Select Git command to execute:
    echo   [AI-Enhanced Commands]
    echo   1. AI Auto Commit ^(automatically generate commit message^)
    echo   2. Pull Request Analysis
    echo   3. Code Quality Analysis
    echo   4. New Feature Implementation Suggestion
    echo   5. AI Full Push ^(add changes, commit with AI message, push^)
    echo   [Standard Git Commands]
    echo   6. Repository Status Check
    echo   7. Pull All Repositories
    echo   8. Push All Repositories
    echo   9. Commit Changes in All Repositories
    echo   10. Switch Branch in All Repositories
    echo   11. Reset Changes in All Repositories
    echo   12. Remove Untracked Files in All Repositories
    echo   [Security/Advanced Operations]
    echo   13. Check Sensitive Information ^(check API keys before pushing^)
    echo   14. Force Pull to Match Remote State
    echo   15. Full Push ^(add, commit, push in one operation^)
    echo   16. Repository Initialization and Initial Commit
    
    set /p "MENU_CHOICE=Enter your choice (1-16): "
    
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
        echo Error: Invalid choice. Please enter a number from 1-16.
        pause
        exit /b 1
    )
)

rem 必要なパラメータの追加入力を促す
if "%COMMAND%"=="analyze-pr" if "%PR_URL%"=="" (
    set /p "PR_URL=Enter PR URL to analyze: "
    if "!PR_URL!"=="" (
        echo Error: PR URL is required.
        exit /b 1
    )
)

if "%COMMAND%"=="analyze-code" if "%FILE_PATH%"=="" (
    set /p "FILE_PATH=Enter file path to analyze: "
    if "!FILE_PATH!"=="" (
        echo Error: File path is required.
        exit /b 1
    )
)

if "%COMMAND%"=="suggest-implementation" if "%FEATURE%"=="" (
    set /p "FEATURE=Describe the feature to implement: "
    if "!FEATURE!"=="" (
        echo Error: Feature description is required.
        exit /b 1
    )
)

if "%COMMAND%"=="commit" if "%COMMIT_MESSAGE%"=="" (
    set /p "COMMIT_MESSAGE=Enter commit message: "
    if "!COMMIT_MESSAGE!"=="" (
        echo Error: Commit message is required.
        exit /b 1
    )
)

if "%COMMAND%"=="checkout" if "%BRANCH%"=="" (
    set /p "BRANCH=Enter branch name to checkout: "
    if "!BRANCH!"=="" (
        echo Error: Branch name is required.
        exit /b 1
    )
)

if "%COMMAND%"=="git-init" if "%GITHUB_URL%"=="" (
    set /p "GITHUB_URL=Enter GitHub repository URL (e.g., https://github.com/username/repo.git): "
    if "!GITHUB_URL!"=="" (
        echo Error: GitHub URL is required.
        goto END
    )
)

rem 再帰検索の確認
if not defined USE_RECURSIVE (
    set /p "RECURSIVE_CHOICE=Search subdirectories recursively? (Y/N): "
    if /i "!RECURSIVE_CHOICE!"=="Y" set "USE_RECURSIVE=--recursive"
)

rem Pythonが利用可能か確認
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

rem 仮想環境の存在確認と有効化
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [INFO] Virtual environment not found. Using system Python.
)

rem git-initコマンドの処理（特別なケース）
if "%COMMAND%"=="git-init" (
    echo [PROCESS] Initializing and configuring repository...
    
    echo Initializing Git repository...
    git -c credential.helper="" -c core.editor=notepad -c core.autocrlf=true init
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to initialize repository.
        goto END
    )
    
    echo Setting remote repository: !GITHUB_URL!
    git -c credential.helper="" remote add origin !GITHUB_URL!
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to set remote repository.
        goto END
    )
    
    echo Creating initial commit...
    git add .
    git -c credential.helper="" commit -m "Initial commit"
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to commit.
        goto END
    )
    
    echo Pushing to remote repository...
    git -c credential.helper="" push -u origin master
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to push.
        goto END
    )
    
    echo Repository initialization and initial commit completed.
    echo Remote repository URL: !GITHUB_URL!
    goto END
)

rem 必要なスクリプトの存在確認
if "%COMMAND%"=="ai-commit" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo Error: OpenAI Git helper script not found: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="analyze-pr" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo Error: OpenAI Git helper script not found: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="analyze-code" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo Error: OpenAI Git helper script not found: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else if "%COMMAND%"=="suggest-implementation" (
    if not exist "%OPENAI_SCRIPT_PATH%" (
        echo Error: OpenAI Git helper script not found: %OPENAI_SCRIPT_PATH%
        goto END
    )
) else (
    if not exist "%GIT_BATCH_SCRIPT%" (
        echo Error: Git batch processing script not found: %GIT_BATCH_SCRIPT%
        goto END
    )
)

rem コマンドの構築と実行
if "%COMMAND%"=="ai-commit" (
    echo Executing AI-assisted commit...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-commit --repo "%REPO_PATH%"
    if !ERRORLEVEL! neq 0 (
        echo Error: An error occurred during AI-assisted commit execution.
        set /a ERROR_COUNT+=1
    )
)

if "%COMMAND%"=="analyze-pr" (
    if not defined PR_URL (
        set /p "PR_URL=Enter pull request URL to analyze: "
    )
    echo [PROCESS] Analyzing pull request %PR_URL%...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" analyze-pr --repo "%REPO_PATH%" --pr-url "%PR_URL%"
    goto END
)

if "%COMMAND%"=="analyze-code" (
    if not defined FILE_PATH (
        set /p "FILE_PATH=Enter file path to analyze: "
    )
    echo [PROCESS] Analyzing file %FILE_PATH%...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" analyze-code --repo "%REPO_PATH%" --file "%FILE_PATH%"
    goto END
)

if "%COMMAND%"=="suggest-implementation" (
    if not defined FEATURE (
        set /p "FEATURE=Describe the feature to implement: "
    )
    echo [PROCESS] Suggesting implementation for "%FEATURE%"...
    if defined TARGET_FILE (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" suggest-implementation --repo "%REPO_PATH%" --feature "%FEATURE%" --target-file "%TARGET_FILE%"
    ) else (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" suggest-implementation --repo "%REPO_PATH%" --feature "%FEATURE%"
    )
    goto END
)

if "%COMMAND%"=="check-sensitive-info" (
    echo [PROCESS] Checking for sensitive information before pushing...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" check-sensitive-info --repo "%REPO_PATH%"
    
    if errorlevel 1 (
        echo [WARNING] Sensitive information detected. Please review before pushing.
        pause
    )
    
    goto END
)

if "%COMMAND%"=="force-pull" (
    echo [PROCESS] Forcing update to match remote state...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" force-pull --repo "%REPO_PATH%"
    goto END
)

if "%COMMAND%"=="full-push" (
    echo [PROCESS] Executing add, commit, and push in one go...
    %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" full-push --repo "%REPO_PATH%"
    goto END
)

if "%COMMAND%"=="ai-full-push" (
    echo Executing AI-assisted full push...
    if defined BRANCH (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-full-push --repo "%REPO_PATH%" --branch "%BRANCH%"
    ) else (
        %PYTHON_CMD% "%OPENAI_SCRIPT_PATH%" ai-full-push --repo "%REPO_PATH%"
    )
    if !ERRORLEVEL! neq 0 (
        echo Error: An error occurred during AI-assisted full push execution.
        set /a ERROR_COUNT+=1
    )
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
echo Git Operations Tool - Command: %COMMAND%
echo Target repository: %REPO_PATH%
if not "%PR_URL%"=="" echo PR URL: %PR_URL%
if not "%FILE_PATH%"=="" echo Target file: %FILE_PATH%
if not "%FEATURE%"=="" echo Feature description: %FEATURE%
if not "%TARGET_FILE%"=="" echo Target file: %TARGET_FILE%
if not "%BRANCH%"=="" echo Branch: %BRANCH%
if not "%COMMIT_MESSAGE%"=="" echo Commit message: %COMMIT_MESSAGE%
if not "%GITHUB_URL%"=="" echo GitHub URL: %GITHUB_URL%
if "%USE_RECURSIVE%"=="--recursive" echo Recursive search: Enabled (max depth: %DEPTH%)
echo ===========================================================
echo.

echo [INFO] Executing Python script...
%PYTHON_CMD% %PYTHON_ARGS%

if errorlevel 1 (
    echo [ERROR] An error occurred during processing.
) else (
    echo [INFO] Processing completed successfully.
)

rem 仮想環境の非アクティブ化
if exist "%VENV_PATH%\Scripts\deactivate.bat" (
    call "%VENV_PATH%\Scripts\deactivate.bat"
)

:END
echo.
pause
endlocal 