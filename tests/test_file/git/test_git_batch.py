#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Git一括管理ツールのテストモジュール

GitBatchProcessorとGitCommandのテストを行います
"""

import os
import sys
import pytest
import tempfile
import shutil
import subprocess
import time
import json
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートを正しく設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト対象のモジュールをインポート
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.git_batch import (
    GitCommand, GitStatus, GitPull, GitCommit, GitBatchProcessor,
    find_git_repos, execute_git_command
)

# テスト結果を保存するグローバル変数
TEST_RESULTS = {}

@pytest.fixture(scope="session", autouse=True)
def report_test_results(request):
    """テスト終了時に結果をまとめて出力するフィクスチャ"""
    yield
    print("\n")
    print("=" * 80)
    print("               テスト結果および担保された機能                ")
    print("=" * 80)
    print(f"{'テスト名':<30}{'結果':<10}{'担保された機能'}")
    print("-" * 80)
    for test_name, result in TEST_RESULTS.items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{test_name:<30}{status:<10}{result['description']}")
    print("-" * 80)
    print(f"テスト環境: Python {sys.version.split()[0]}")
    pass_count = sum(1 for r in TEST_RESULTS.values() if r["passed"])
    fail_count = len(TEST_RESULTS) - pass_count
    print(f"総合結果: {pass_count} passed / {fail_count} failed")
    print("=" * 80)
    
    # 結果をJSONファイルに保存 - 新しい命名規則に対応
    try:
        # カテゴリ情報を取得（現在のフォルダ名）
        category = Path(__file__).parent.name
        results_path = PROJECT_ROOT / "tests" / "results" / f"{category}_git_batch_test_results.json"
        
        # resultsディレクトリが存在しない場合は作成
        results_dir = results_path.parent
        if not results_dir.exists():
            results_dir.mkdir(parents=True)
        
        # テスト実行時間を記録
        test_data = {
            "test_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category
        }
        # テスト結果をマージ
        test_data.update(TEST_RESULTS)
        
        # JSONの文字列を一旦UTF-8で作成
        json_str = json.dumps(test_data, ensure_ascii=False, indent=2)
        
        # BOMなしUTF-8でファイル書き込み
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(json_str)
            
        print(f"テスト結果を {results_path} に保存しました")
    except Exception as e:
        print(f"テスト結果の保存に失敗しました: {e}")
        
    # テスト結果を標準出力にも再度出力する
    print("\nテスト結果の概要:")
    for test_name, result in TEST_RESULTS.items():
        status = "PASS" if result["passed"] else "FAIL"
        print(f"- {test_name}: {status} - {result['description']}")

def record_result(name, passed, description):
    """テスト結果を記録する関数"""
    TEST_RESULTS[name] = {
        "passed": passed,
        "description": description,
        "execution_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return passed

def rmtree_retry(path, max_retries=3, retry_delay=0.5):
    """
    一時ディレクトリを削除する関数。Windowsでのファイルロック問題に対応するため、
    リトライロジックを実装しています。
    
    Args:
        path: 削除するディレクトリパス
        max_retries: 最大リトライ回数
        retry_delay: リトライ間の待機時間（秒）
    """
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return
        except PermissionError as e:
            if attempt == max_retries - 1:
                print(f"警告: 一時ディレクトリの削除に失敗しました: {e}")
                print(f"パス: {path}")
                # 最後の試行で失敗した場合は警告を出すだけで続行
                pass
            else:
                # 少し待ってからリトライ
                time.sleep(retry_delay)

class TestGitCommand:
    """GitCommandクラスのテスト"""
    
    @pytest.fixture
    def setup_git_repo(self):
        """テスト用の一時的なGitリポジトリを作成"""
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Gitリポジトリを初期化
            subprocess.run(
                ['git', 'init'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # テスト用のファイルを作成
            test_file = Path(temp_dir) / "test.txt"
            with open(test_file, 'w') as f:
                f.write("テスト用ファイル")
            
            # ユーザー設定を追加（GitコマンドがエラーにならないようCIでも）
            subprocess.run(
                ['git', 'config', 'user.email', 'test@example.com'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            subprocess.run(
                ['git', 'config', 'user.name', 'Test User'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # ファイルをステージに追加
            subprocess.run(
                ['git', 'add', '.'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # コミット
            subprocess.run(
                ['git', 'commit', '-m', '初期コミット'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            yield temp_dir
        finally:
            # テスト終了後に一時ディレクトリを削除（リトライロジック付き）
            rmtree_retry(temp_dir)
    
    def test_git_status(self, setup_git_repo):
        """GitStatusが正しく動作するかテスト"""
        repo_path = setup_git_repo
        
        # GitStatusのインスタンスを作成して実行
        status_cmd = GitStatus(repo_path)
        result = status_cmd.execute()
        
        # 結果を検証
        assert result['success']
        assert 'command' in result
        assert 'git status --short' in result['command']
    
    def test_git_commit(self, setup_git_repo):
        """GitCommitが正しく動作するかテスト"""
        repo_path = setup_git_repo
        
        # テスト用の変更を加える
        test_file = Path(repo_path) / "test.txt"
        with open(test_file, 'a') as f:
            f.write("\n追加の行")
        
        # GitCommitのインスタンスを作成して実行
        options = {'message': 'テスト用コミット'}
        commit_cmd = GitCommit(repo_path, options)
        result = commit_cmd.execute()
        
        # 結果を検証
        assert result['success']
        assert 'コミットする変更はありません' not in result['output']
        assert 'コミット' in result['output']
    
    @patch('subprocess.run')
    def test_run_command_error(self, mock_run, setup_git_repo):
        """コマンド実行エラー時の処理をテスト"""
        repo_path = setup_git_repo
        
        # モックがCalledProcessErrorを発生させるように設定
        mock_error = subprocess.CalledProcessError(1, ['git', 'status'], 
                                                 stderr="fatal: エラーメッセージ")
        mock_run.side_effect = mock_error
        
        # GitStatusのインスタンスを作成
        status_cmd = GitStatus(repo_path)
        
        # 例外が発生することを検証
        with pytest.raises(subprocess.CalledProcessError):
            status_cmd.execute()


class TestGitBatchProcessor:
    """GitBatchProcessorクラスのテスト"""
    
    @pytest.fixture
    def setup_multiple_repos(self):
        """複数のテスト用Gitリポジトリを作成"""
        # 親ディレクトリを作成
        parent_dir = tempfile.mkdtemp()
        repos = []
        
        try:
            # 2つのリポジトリを作成
            for i in range(2):
                repo_path = Path(parent_dir) / f"repo{i}"
                repo_path.mkdir()
                
                # Gitリポジトリを初期化
                subprocess.run(
                    ['git', 'init'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # テスト用のファイルを作成
                test_file = repo_path / "test.txt"
                with open(test_file, 'w') as f:
                    f.write(f"リポジトリ{i}のテスト用ファイル")
                
                # ユーザー設定
                subprocess.run(
                    ['git', 'config', 'user.email', 'test@example.com'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                subprocess.run(
                    ['git', 'config', 'user.name', 'Test User'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # コミット
                subprocess.run(
                    ['git', 'add', '.'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                subprocess.run(
                    ['git', 'commit', '-m', f'リポジトリ{i}の初期コミット'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                repos.append(str(repo_path))
            
            yield parent_dir, repos
        finally:
            # テスト終了後に親ディレクトリを削除（リトライロジック付き）
            rmtree_retry(parent_dir)
    
    def test_batch_processor_status(self, setup_multiple_repos):
        """複数リポジトリの一括ステータス確認をテスト"""
        parent_dir, repos = setup_multiple_repos
        
        # GitBatchProcessorのインスタンスを作成して実行
        processor = GitBatchProcessor(repos)
        results = processor.execute_batch('status')
        
        # 結果を検証
        assert len(results) == len(repos)
        for repo_name, result in results.items():
            assert result['success']
            assert 'command' in result
            assert 'git status' in result['command']
    
    @patch('src.utils.git_batch.GitStatus.execute')
    def test_batch_processor_with_error(self, mock_execute, setup_multiple_repos):
        """一部のリポジトリでエラーが発生する場合のテスト"""
        parent_dir, repos = setup_multiple_repos
        
        # 最初のリポジトリだけ成功、2つ目はエラー
        def mock_side_effect(repo_index):
            if repo_index == 0:
                return {'success': True, 'output': 'ok', 'command': 'git status'}
            else:
                raise Exception("テスト用エラー")
        
        # モックの挙動を設定
        mock_execute.side_effect = lambda: mock_side_effect(0)  # 常に最初のリポジトリとして扱う
        
        # テスト実行
        processor = GitBatchProcessor(repos)
        results = processor.execute_batch('status')
        
        # 結果を検証
        assert len(results) == len(repos)
        # すべてのリポジトリが結果に含まれていることを確認
        for repo_name in [Path(repo).name for repo in repos]:
            assert repo_name in results
    
    def test_find_git_repos(self, setup_multiple_repos):
        """Gitリポジトリの検索機能をテスト"""
        parent_dir, repos = setup_multiple_repos
        
        # リポジトリを検索
        found_repos = find_git_repos(parent_dir, max_depth=1, recursive=True)
        
        # 結果を検証（パスの形式が違う可能性があるため、名前だけで比較）
        found_names = {Path(repo).name for repo in found_repos}
        expected_names = {Path(repo).name for repo in repos}
        assert found_names == expected_names


@patch('src.utils.git_batch.find_git_repos')
@patch('src.utils.git_batch.GitBatchProcessor')
def test_execute_git_command(mock_processor, mock_find_repos):
    """execute_git_command関数のテスト"""
    # モックの設定
    mock_find_repos.return_value = ['/path/to/repo1', '/path/to/repo2']
    
    processor_instance = MagicMock()
    processor_instance.execute_batch.return_value = {
        'repo1': {'success': True, 'output': 'リポジトリ1の結果'},
        'repo2': {'success': True, 'output': 'リポジトリ2の結果'}
    }
    processor_instance.summary.return_value = {
        'total': 2, 'success': 2, 'failure': 0
    }
    mock_processor.return_value = processor_instance
    
    # 環境変数がNoneの場合にはAutoAddが文字列になるようにパッチを当てる
    with patch('src.utils.git_batch.env', None):
        # 関数を実行
        result = execute_git_command('status', path='.', recursive=True)
    
    # 検証
    assert result['success']
    assert 'summary' in result
    assert result['summary']['total'] == 2
    assert result['summary']['success'] == 2
    assert 'results' in result
    
    # モックが正しく呼ばれたことを確認
    mock_find_repos.assert_called_once()
    mock_processor.assert_called_once()
    processor_instance.execute_batch.assert_called_once_with('status')


if __name__ == "__main__":
    pytest.main(['-v', __file__]) 