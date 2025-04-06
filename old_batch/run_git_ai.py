#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Git操作ツール（OpenAI API対応）

Git操作を補助し、OpenAI APIを利用した高度な機能を提供します。
このスクリプトはrun_git_ai.batの代替として、文字化けの問題を解決します。

使用方法:
    python run_git_ai.py [コマンド] [オプション]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


# 定数定義
VENV_PATH = Path("venv")
PYTHON_CMD = "python"
OPENAI_SCRIPT_PATH = Path("src/utils/openai_git_helper.py")
GIT_BATCH_SCRIPT = Path("src/utils/git_batch.py")
DEFAULT_REPO_PATH = "."


def check_python():
    """Pythonが利用可能か確認"""
    try:
        subprocess.run(["python", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: Python not found.")
        print("Please make sure Python is installed.")
        return False


def setup_virtual_env():
    """仮想環境のセットアップ"""
    if not VENV_PATH.exists():
        print("Virtual environment not found. Creating new one...")
        try:
            subprocess.run(["python", "-m", "venv", str(VENV_PATH)], check=True)
            print("Virtual environment created.")
        except subprocess.SubprocessError:
            print("Failed to create virtual environment.")
            return False
    
    # 仮想環境のアクティベート（直接実行ではなく環境変数を設定）
    if sys.platform.startswith('win'):
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python"
    
    if not venv_python.exists():
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False
        
    print("Virtual environment activated.")
    return str(venv_python)


def show_help():
    """ヘルプメッセージの表示"""
    print("===== Git Operations Tool with OpenAI API =====")
    print("Usage:")
    print("  python run_git_ai.py [command] [options]")
    print()
    print("Commands:")
    print("  ai-commit             : Generate commit message from changes and commit")
    print("  analyze-pr            : Analyze and summarize a pull request")
    print("  analyze-code          : Analyze code quality of specified file")
    print("  suggest-implementation: Suggest implementation for a new feature")
    print("  status                : Show status of all repositories")
    print("  pull                  : Execute pull on all repositories")
    print("  push                  : Execute push on all repositories")
    print("  commit                : Commit changes in all repositories")
    print("  checkout              : Checkout specified branch in all repositories")
    print("  reset                 : Reset changes in all repositories")
    print("  clean                 : Remove untracked files in all repositories")
    print("  check-sensitive-info  : Check for sensitive information before pushing")
    print("  force-pull            : Force update to match remote state")
    print("  full-push             : Execute add, commit, and push in one go")
    print("  ai-full-push          : Execute add, commit with AI-generated message, and push")
    print("  git-init              : Initialize repository, set GitHub URL, check sensitive info, initial commit")
    print()
    print("Options:")
    print("  --repo <dir>         : Specify Git repository path (default: current directory)")
    print("  --branch <name>      : Specify branch name (for checkout, pull commands)")
    print("  --message <msg>      : Specify commit message")
    print("  --pr-url <url>       : URL of the pull request to analyze")
    print("  --file <path>        : File path to analyze")
    print("  --feature <desc>     : Description of feature to implement")
    print("  --target-file <file> : Target file name to implement feature")
    print("  --recursive          : Search subdirectories recursively (default: disabled)")
    print("  --depth <num>        : Maximum depth for recursive search (default: 2)")
    print("  --github-url <url>   : GitHub repository URL (for git-init command)")
    print("  --help               : Display this help message")
    print()
    print("Examples:")
    print("  python run_git_ai.py ai-commit")
    print("  python run_git_ai.py analyze-pr --pr-url https://github.com/user/repo/pull/123")
    print("  python run_git_ai.py analyze-code --file src/main.py")
    print("  python run_git_ai.py suggest-implementation --feature \"Implement GitHub Issue summarization\"")
    print("  python run_git_ai.py pull --branch main --recursive")
    print("  python run_git_ai.py commit --message \"Update commit\"")
    print("  python run_git_ai.py git-init --github-url https://github.com/username/repo.git")


def show_menu():
    """メニューの表示と選択"""
    print("Select Git command to execute:")
    print("  [AI-Enhanced Commands]")
    print("  1. AI Auto Commit (automatically generate commit message)")
    print("  2. Pull Request Analysis")
    print("  3. Code Quality Analysis")
    print("  4. New Feature Implementation Suggestion")
    print("  5. AI Full Push (add changes, commit with AI message, push)")
    print("  [Standard Git Commands]")
    print("  6. Repository Status Check")
    print("  7. Pull All Repositories")
    print("  8. Push All Repositories")
    print("  9. Commit Changes in All Repositories")
    print("  10. Switch Branch in All Repositories")
    print("  11. Reset Changes in All Repositories")
    print("  12. Remove Untracked Files in All Repositories")
    print("  [Security/Advanced Operations]")
    print("  13. Check Sensitive Information (check API keys before pushing)")
    print("  14. Force Pull to Match Remote State")
    print("  15. Full Push (add, commit, push in one operation)")
    print("  16. Repository Initialization and Initial Commit")
    
    commands = {
        "1": "ai-commit",
        "2": "analyze-pr",
        "3": "analyze-code",
        "4": "suggest-implementation",
        "5": "ai-full-push",
        "6": "status",
        "7": "pull",
        "8": "push",
        "9": "commit",
        "10": "checkout",
        "11": "reset",
        "12": "clean",
        "13": "check-sensitive-info",
        "14": "force-pull",
        "15": "full-push",
        "16": "git-init"
    }
    
    while True:
        try:
            choice = input("Enter your choice (1-16): ")
            if choice in commands:
                return commands[choice]
            else:
                print("Error: Invalid choice. Please enter a number from 1-16.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)


def git_init(args):
    """Gitリポジトリの初期化と初期コミット"""
    print("[PROCESS] Initializing and configuring repository...")
    
    # 環境変数の設定
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["EDITOR"] = "notepad"
    env["GIT_EDITOR"] = "notepad"
    env["GIT_TERMINAL_PROMPT"] = "1"
    env["GIT_CREDENTIAL_HELPER"] = ""
    
    # Gitリポジトリの初期化
    print(f"Initializing Git repository...")
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "core.editor=notepad", "-c", "core.autocrlf=true", "init"],
        env=env, check=False
    )
    if result.returncode != 0:
        print("Error: Failed to initialize repository.")
        return 1
    
    # リモートリポジトリの設定
    print(f"Setting remote repository: {args.github_url}")
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "remote", "add", "origin", args.github_url],
        env=env, check=False
    )
    if result.returncode != 0:
        print("Warning: Failed to add remote origin. Trying to update URL...")
        subprocess.run(
            ["git", "-c", "credential.helper=", "remote", "set-url", "origin", args.github_url],
            env=env, check=False
        )
    
    # 初期コミット
    print("Creating initial commit...")
    subprocess.run(["git", "add", "."], env=env, check=False)
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "commit", "-m", "Initial commit"],
        env=env, check=False
    )
    if result.returncode != 0:
        print("Error: Failed to commit.")
        return 1
    
    # プッシュ
    print("Pushing to master branch...")
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "push", "-u", "origin", "master"],
        env=env, check=False
    )
    if result.returncode != 0:
        print("Error: Failed to push.")
        return 1
    
    print("Repository initialization and initial commit completed.")
    print(f"Remote repository URL: {args.github_url}")
    return 0


def execute_ai_command(python_exe, command, args):
    """AI拡張コマンドの実行"""
    if not OPENAI_SCRIPT_PATH.exists():
        print(f"Error: OpenAI Git helper script not found: {OPENAI_SCRIPT_PATH}")
        return 1
    
    cmd = [python_exe, str(OPENAI_SCRIPT_PATH), command]
    
    # 引数の追加
    cmd.extend(["--repo", args.repo])
    
    if command == "analyze-pr" and args.pr_url:
        cmd.extend(["--pr-url", args.pr_url])
    elif command == "analyze-code" and args.file:
        cmd.extend(["--file", args.file])
    elif command == "suggest-implementation" and args.feature:
        cmd.extend(["--feature", args.feature])
        if args.target_file:
            cmd.extend(["--target-file", args.target_file])
    elif command == "ai-full-push" and args.branch:
        cmd.extend(["--branch", args.branch])
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def execute_git_command(python_exe, command, args):
    """通常のGitコマンドの実行"""
    if not GIT_BATCH_SCRIPT.exists():
        print(f"Error: Git batch processing script not found: {GIT_BATCH_SCRIPT}")
        return 1
    
    cmd = [
        python_exe, 
        str(GIT_BATCH_SCRIPT), 
        command, 
        "--path", args.repo, 
        "--depth", str(args.depth)
    ]
    
    if args.recursive:
        cmd.append("--recursive")
    
    if command in ["checkout", "pull"] and args.branch:
        cmd.extend(["--branch", args.branch])
    
    if command == "commit" and args.message:
        cmd.extend(["--message", args.message])
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """メイン処理"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description="Git Operations Tool with OpenAI API",
        add_help=False  # カスタムヘルプを使用するため
    )
    
    # コマンド
    parser.add_argument("command", nargs="?", default=None,
                        help="Git operation to perform")
    
    # オプション
    parser.add_argument("--help", action="store_true",
                        help="Show help message")
    parser.add_argument("--repo", default=DEFAULT_REPO_PATH,
                        help="Git repository path")
    parser.add_argument("--branch", 
                        help="Branch name for checkout/pull operations")
    parser.add_argument("--message", 
                        help="Commit message")
    parser.add_argument("--pr-url", 
                        help="URL of the pull request to analyze")
    parser.add_argument("--file", 
                        help="File path to analyze")
    parser.add_argument("--feature", 
                        help="Description of feature to implement")
    parser.add_argument("--target-file", 
                        help="Target file name for implementation")
    parser.add_argument("--recursive", action="store_true",
                        help="Search subdirectories recursively")
    parser.add_argument("--depth", type=int, default=2,
                        help="Maximum depth for recursive search")
    parser.add_argument("--github-url", 
                        help="GitHub repository URL for git-init command")
    
    # 引数を解析
    args = parser.parse_args()
    
    # ヘルプ表示
    if args.help or (len(sys.argv) == 1 and not args.command):
        show_help()
        return 0
    
    # コマンドが指定されていない場合、メニューを表示
    if not args.command:
        args.command = show_menu()
    
    # Pythonが利用可能か確認
    if not check_python():
        return 1
    
    # 仮想環境のセットアップ
    python_exe = setup_virtual_env()
    if not python_exe:
        # システムのPythonを使用
        python_exe = PYTHON_CMD
    
    # 追加のパラメータを要求
    if args.command == "analyze-pr" and not args.pr_url:
        args.pr_url = input("Enter PR URL to analyze: ")
        if not args.pr_url:
            print("Error: PR URL is required.")
            return 1
    
    if args.command == "analyze-code" and not args.file:
        args.file = input("Enter file path to analyze: ")
        if not args.file:
            print("Error: File path is required.")
            return 1
    
    if args.command == "suggest-implementation" and not args.feature:
        args.feature = input("Describe the feature to implement: ")
        if not args.feature:
            print("Error: Feature description is required.")
            return 1
    
    if args.command == "commit" and not args.message:
        args.message = input("Enter commit message: ")
        if not args.message:
            print("Error: Commit message is required.")
            return 1
    
    if args.command == "checkout" and not args.branch:
        args.branch = input("Enter branch name to checkout: ")
        if not args.branch:
            print("Error: Branch name is required.")
            return 1
    
    if args.command == "git-init" and not args.github_url:
        args.github_url = input("Enter GitHub repository URL (e.g., https://github.com/username/repo.git): ")
        if not args.github_url:
            print("Error: GitHub URL is required.")
            return 1
    
    # 再帰的検索の確認
    if not args.recursive:
        recursive_choice = input("Search subdirectories recursively? (Y/N): ")
        if recursive_choice.upper() == "Y":
            args.recursive = True
    
    # コマンド実行前の情報表示
    print("\n===========================================================")
    print(f"Git Operations Tool - Command: {args.command}")
    print(f"Target repository: {args.repo}")
    if args.pr_url:
        print(f"PR URL: {args.pr_url}")
    if args.file:
        print(f"Target file: {args.file}")
    if args.feature:
        print(f"Feature description: {args.feature}")
    if args.target_file:
        print(f"Target file: {args.target_file}")
    if args.branch:
        print(f"Branch: {args.branch}")
    if args.message:
        print(f"Commit message: {args.message}")
    if args.github_url:
        print(f"GitHub URL: {args.github_url}")
    if args.recursive:
        print(f"Recursive search: Enabled (max depth: {args.depth})")
    print("===========================================================\n")
    
    # コマンド実行
    if args.command == "git-init":
        return git_init(args)
    elif args.command in ["ai-commit", "analyze-pr", "analyze-code", "suggest-implementation", 
                          "check-sensitive-info", "force-pull", "full-push", "ai-full-push"]:
        return execute_ai_command(python_exe, args.command, args)
    else:
        return execute_git_command(python_exe, args.command, args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    finally:
        input("\nPress Enter to exit...") 