#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Git一括管理ツール (Python実装)

複数のGitリポジトリに対して一括操作を行うPythonモジュール
"""

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# 設定管理とロギングのインポート
try:
    from src.utils.environment import env
    from src.utils.logging_config import get_logger
except ImportError:
    # 直接実行時のフォールバック
    import logging
    env = None
    logging.basicConfig(level=logging.INFO)
    get_logger = lambda name: logging.getLogger(name)

# ロガー設定
logger = get_logger(__name__)


class GitCommand:
    """Git操作の基本クラス"""
    
    def __init__(self, repo_path: str, options: Dict[str, Any] = None):
        """
        コンストラクタ
        
        Args:
            repo_path: Gitリポジトリのパス
            options: コマンドオプション
        """
        self.repo_path = Path(repo_path)
        self.options = options or {}
        
        # リポジトリの存在確認
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"有効なGitリポジトリではありません: {repo_path}")
    
    def _run_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """
        Gitコマンドを実行
        
        Args:
            command: 実行するコマンドとその引数のリスト
        
        Returns:
            実行結果
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                check=True,
                text=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"コマンド実行エラー: {e.stderr.strip()}")
            raise
    
    def execute(self) -> Dict[str, Any]:
        """
        コマンドを実行する抽象メソッド
        
        Returns:
            実行結果の辞書
        """
        raise NotImplementedError("サブクラスで実装する必要があります")


class GitStatus(GitCommand):
    """リポジトリのステータスを表示"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git statusを実行
        
        Returns:
            実行結果
        """
        command = ['git', 'status', '--short']
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitPull(GitCommand):
    """リモートリポジトリからプルする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git pullを実行
        
        Returns:
            実行結果
        """
        branch = self.options.get('branch', '')
        command = ['git', 'pull']
        if branch:
            command.extend(['origin', branch])
        
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitForcePull(GitCommand):
    """リモートリポジトリから強制的にプルする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git fetch と git reset --hard origin/<branch> を実行して強制的にリモートの状態に合わせる
        
        Returns:
            実行結果
        """
        branch = self.options.get('branch', '')
        if not branch:
            # カレントブランチを取得
            try:
                branch_result = self._run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
                branch = branch_result.stdout.strip()
            except Exception as e:
                return {
                    'success': False,
                    'error': f"カレントブランチの取得に失敗しました: {str(e)}",
                    'command': 'git rev-parse --abbrev-ref HEAD'
                }
        
        # まずはfetchを実行
        try:
            fetch_result = self._run_command(['git', 'fetch', 'origin'])
        except Exception as e:
            return {
                'success': False,
                'error': f"fetchに失敗しました: {str(e)}",
                'command': 'git fetch origin'
            }
        
        # ローカルの変更を保存するかどうか
        try_stash = self.options.get('try_stash', True)
        
        if try_stash:
            # ローカルの変更を一時保存
            try:
                stash_result = self._run_command(['git', 'stash', 'save', f"自動保存 {time.strftime('%Y-%m-%d %H:%M:%S')}"])
                stashed = "No local changes to save" not in stash_result.stdout
            except Exception:
                stashed = False
        
        # 強制的にリモートの状態にリセット
        try:
            reset_result = self._run_command(['git', 'reset', '--hard', f"origin/{branch}"])
            
            result = {
                'success': reset_result.returncode == 0,
                'output': f"強制的にリセットしました: {reset_result.stdout.strip()}",
                'command': f"git reset --hard origin/{branch}"
            }
            
            # stashした場合は、変更を戻す試み
            if try_stash and stashed:
                try:
                    self._run_command(['git', 'stash', 'pop'])
                    result['output'] += "\n保存した変更を復元しました。"
                except Exception as e:
                    result['output'] += f"\n保存した変更の復元に失敗しました: {str(e)}"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"リセットに失敗しました: {str(e)}",
                'command': f"git reset --hard origin/{branch}"
            }


class GitPush(GitCommand):
    """リモートリポジトリにプッシュする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git pushを実行
        
        Returns:
            実行結果
        """
        branch = self.options.get('branch', '')
        command = ['git', 'push']
        if branch:
            command.extend(['origin', branch])
        
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitFullPush(GitCommand):
    """変更をadd, commit, pushまで一気に実行する"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git add, git commit, git pushを連続して実行
        
        Returns:
            実行結果
        """
        # 変更があるか確認
        status_result = self._run_command(['git', 'status', '--porcelain'])
        if not status_result.stdout.strip():
            return {
                'success': True,
                'output': "変更はありません。プッシュするものがありません。",
                'command': 'git status'
            }
        
        # 変更をステージングエリアに追加
        try:
            add_result = self._run_command(['git', 'add', '--all'])
        except Exception as e:
            return {
                'success': False,
                'error': f"変更の追加に失敗しました: {str(e)}",
                'command': 'git add --all'
            }
        
        # コミット実行
        commit_message = self.options.get('message', f"自動コミット {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            commit_result = self._run_command(['git', 'commit', '-m', commit_message])
        except Exception as e:
            return {
                'success': False,
                'error': f"コミットに失敗しました: {str(e)}",
                'command': f"git commit -m '{commit_message}'"
            }
        
        # プッシュ実行
        branch = self.options.get('branch', '')
        push_command = ['git', 'push']
        if branch:
            push_command.extend(['origin', branch])
        
        try:
            push_result = self._run_command(push_command)
            
            return {
                'success': True,
                'output': f"変更を追加、コミット、プッシュしました。\nコミットメッセージ: {commit_message}\n{push_result.stdout.strip()}",
                'command': ' '.join(push_command)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"プッシュに失敗しました: {str(e)}",
                'command': ' '.join(push_command)
            }


class GitCommit(GitCommand):
    """変更をコミットする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git addとgit commitを実行
        
        Returns:
            実行結果
        """
        message = self.options.get('message', 'Auto commit by batch tool')
        
        # 変更を全て追加
        add_result = self._run_command(['git', 'add', '--all'])
        
        # 変更があるか確認
        status_result = self._run_command(['git', 'status', '--porcelain'])
        if status_result and not status_result.stdout.strip():
            return {
                'success': True,
                'output': 'コミットする変更はありません',
                'command': 'git status'
            }
        
        commit_result = self._run_command(['git', 'commit', '-m', message])
        return {
            'success': commit_result.returncode == 0,
            'output': commit_result.stdout.strip() if commit_result and commit_result.stdout else '',
            'command': f'git commit -m "{message}"'
        }


class GitCheckout(GitCommand):
    """指定されたブランチにチェックアウトする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git checkoutを実行
        
        Returns:
            実行結果
        """
        branch = self.options.get('branch', '')
        if not branch:
            raise ValueError("ブランチ名が指定されていません")
        
        command = ['git', 'checkout', branch]
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitReset(GitCommand):
    """変更をリセットする"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git reset --hardを実行
        
        Returns:
            実行結果
        """
        command = ['git', 'reset', '--hard', 'HEAD']
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitClean(GitCommand):
    """追跡されていないファイルを削除する"""
    
    def execute(self) -> Dict[str, Any]:
        """
        git cleanを実行
        
        Returns:
            実行結果
        """
        command = ['git', 'clean', '-fd']
        result = self._run_command(command)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'command': ' '.join(command)
        }


class GitBatchProcessor:
    """複数リポジトリに対するGitバッチ処理"""
    
    def __init__(self, repos: List[str], options: Dict[str, Any] = None):
        """
        コンストラクタ
        
        Args:
            repos: 処理対象のリポジトリパスのリスト
            options: 全リポジトリ共通のオプション
        """
        self.repos = repos
        self.options = options or {}
        self.results = {}
        
        # コマンドクラスのマッピング
        self.command_classes = {
            'status': GitStatus,
            'pull': GitPull,
            'force-pull': GitForcePull,
            'push': GitPush,
            'full-push': GitFullPush,
            'commit': GitCommit,
            'checkout': GitCheckout,
            'reset': GitReset,
            'clean': GitClean
        }
    
    def execute_batch(self, command_name: str) -> Dict[str, Any]:
        """
        全リポジトリに対して指定されたコマンドを実行
        
        Args:
            command_name: 実行するコマンド名
        
        Returns:
            リポジトリごとの実行結果
        """
        if command_name not in self.command_classes:
            raise ValueError(f"不明なコマンド: {command_name}")
        
        command_class = self.command_classes[command_name]
        results = {}
        
        for repo in self.repos:
            repo_name = Path(repo).name
            logger.info(f"リポジトリ処理開始: {repo_name}")
            
            try:
                command = command_class(repo, self.options)
                result = command.execute()
                results[repo_name] = result
                logger.info(f"結果: {result['output']}")
            except Exception as e:
                logger.error(f"エラー発生: {str(e)}")
                results[repo_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        self.results.update(results)
        return results
    
    def summary(self) -> Dict[str, int]:
        """
        実行結果のサマリーを取得
        
        Returns:
            成功/失敗数のサマリー
        """
        success_count = sum(1 for result in self.results.values() if result.get('success', False))
        return {
            'total': len(self.results),
            'success': success_count,
            'failure': len(self.results) - success_count
        }


def find_git_repos(base_dir: str, max_depth: int = 2, recursive: bool = False) -> List[str]:
    """
    指定ディレクトリ以下のGitリポジトリを検索
    
    Args:
        base_dir: 検索を開始するディレクトリ
        max_depth: 最大の検索深さ
        recursive: サブディレクトリを再帰的に検索するかどうか
    
    Returns:
        Gitリポジトリのパスのリスト
    """
    base_path = Path(base_dir).resolve()
    
    # リポジトリの一覧を保持するリスト
    git_repos = []
    
    # まず指定ディレクトリ自体がGitリポジトリかチェック
    if (base_path / ".git").exists():
        git_repos.append(str(base_path))
        # 再帰的でない場合はここで終了
        if not recursive:
            return git_repos
    
    # 再帰的に検索
    return _find_git_repos_recursive(base_path, 1, max_depth)


def _find_git_repos_recursive(path: Path, current_depth: int, max_depth: int) -> List[str]:
    """
    再帰的にGitリポジトリを検索する内部関数
    
    Args:
        path: 検索するディレクトリのパス
        current_depth: 現在の検索深さ
        max_depth: 最大検索深さ
    
    Returns:
        Gitリポジトリのパスのリスト
    """
    # 最大深さを超えた場合は空リストを返す
    if current_depth > max_depth:
        return []
    
    git_repos = []
    
    try:
        # ディレクトリ内の項目を走査
        for item in path.iterdir():
            if item.is_dir():
                # .gitディレクトリがある場合はリポジトリとして追加
                if (item / ".git").exists():
                    git_repos.append(str(item))
                # さらに深く検索
                git_repos.extend(_find_git_repos_recursive(item, current_depth + 1, max_depth))
    except PermissionError:
        # アクセス権限がない場合はスキップ
        logger.warning(f"アクセス権限がありません: {path}")
    except Exception as e:
        logger.error(f"ディレクトリ検索中にエラー: {path}, {str(e)}")
    
    return git_repos


def execute_git_command(command: str, **kwargs) -> Dict[str, Any]:
    """
    指定されたGitコマンドを実行する汎用関数
    
    Args:
        command: 実行するGitコマンド名
        **kwargs: コマンドのオプション
    
    Returns:
        実行結果
    """
    # パラメータの取得
    repo_path = kwargs.get("path", ".")
    branch = kwargs.get("branch", "")
    message = kwargs.get("message", "")
    auto_add = kwargs.get("auto_add", False)
    recursive = kwargs.get("recursive", False)
    max_depth = kwargs.get("max_depth", 2)
    
    # 存在チェック
    if not os.path.exists(repo_path):
        return {"error": f"指定されたパスが存在しません: {repo_path}", "success": False}
    
    # 単一リポジトリか複数リポジトリか判断
    repos = []
    
    if recursive:
        # 再帰的に検索
        repos = find_git_repos(repo_path, max_depth=max_depth, recursive=True)
    else:
        # 指定パスが直接リポジトリかチェック
        git_dir = os.path.join(repo_path, ".git")
        if os.path.exists(git_dir):
            repos = [repo_path]
    
    if not repos:
        return {"error": f"Gitリポジトリが見つかりませんでした: {repo_path}", "success": False}
    
    # オプションの組み立て
    options = {}
    if branch:
        options["branch"] = branch
    if message:
        options["message"] = message
    if isinstance(auto_add, str):
        options["auto_add"] = auto_add.lower() == "true"
    else:
        options["auto_add"] = bool(auto_add)
    
    # GitBatchProcessorを使って実行
    processor = GitBatchProcessor(repos, options)
    results = processor.execute_batch(command)
    
    # 結果のサマリーも追加
    summary = processor.summary()
    
    # 成功フラグを設定
    success = summary['failure'] == 0 and summary['total'] > 0
    
    return {
        "results": results,
        "summary": summary,
        "success": success
    }


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description='Git一括処理ツール')
    
    parser.add_argument('command', choices=['status', 'pull', 'force-pull', 'push', 'full-push', 'commit', 'checkout', 'reset', 'clean'],
                        help='実行するGitコマンド')
    parser.add_argument('--path', default='.', help='処理対象の基底ディレクトリ')
    parser.add_argument('--branch', help='対象ブランチ（checkout, pullコマンド用）')
    parser.add_argument('--message', '-m', help='コミットメッセージ（commitコマンド用）')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも再帰的に検索')
    parser.add_argument('--depth', type=int, default=2, help='再帰検索時の最大深度')
    parser.add_argument('--no-stash', action='store_true', help='force-pull時にstashを試みない')
    
    return parser.parse_args()


def main():
    """メイン関数"""
    args = parse_args()
    
    # 対象リポジトリを探索
    logger.info(f"リポジトリ探索開始: {args.path}")
    repos = find_git_repos(args.path, args.depth, args.recursive)
    
    if not repos:
        logger.error("Gitリポジトリが見つかりませんでした。")
        return 1
    
    logger.info(f"{len(repos)}個のリポジトリが見つかりました:")
    for repo in repos:
        logger.info(f"- {repo}")
    
    # オプションの設定
    options = {}
    if args.branch:
        options['branch'] = args.branch
    if args.message:
        options['message'] = args.message
    if args.no_stash:
        options['try_stash'] = False
    
    # バッチ処理実行
    result = execute_git_command(
        args.command,
        path=args.path,
        branch=args.branch,
        message=args.message,
        recursive=args.recursive,
        depth=args.depth
    )
    
    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)


# スクリプトとして直接実行された場合のエントリーポイント
if __name__ == "__main__":
    main() 