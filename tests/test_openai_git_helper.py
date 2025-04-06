#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI Gitヘルパーのテストモジュール

OpenAIGitHelperクラスのテストを行います
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.openai_git_helper import OpenAIGitHelper

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


class TestOpenAIGitHelper:
    """OpenAIGitHelperクラスのテスト"""
    
    @pytest.fixture
    def setup_git_repo(self):
        """テスト用のGitリポジトリを作成"""
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
            test_file = Path(temp_dir) / "test.py"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('def hello():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    hello()')
            
            # テスト用のファイル2を作成（変更用）
            test_file2 = Path(temp_dir) / "config.py"
            with open(test_file2, 'w', encoding='utf-8') as f:
                f.write('# 設定ファイル\nAPI_URL = "https://example.com/api"')
            
            # ユーザー設定を追加
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
            
            # ファイルをステージに追加してコミット
            subprocess.run(
                ['git', 'add', '.'],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
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
    
    @pytest.fixture
    def openai_helper(self):
        """OpenAIGitHelperのインスタンスを作成（適切にモック）"""
        # _get_config_valueメソッドをパッチして設定をモック
        with patch.object(OpenAIGitHelper, '_get_config_value') as mock_config:
            # 設定値をモックで返す
            mock_config.side_effect = lambda section, key, default: {
                ('GIT', 'use_openai', 'true'): 'true',
                ('OPENAI', 'api_key', ''): 'test-api-key',
                ('OPENAI', 'model', 'gpt-3.5-turbo'): 'gpt-3.5-turbo',
            }.get((section, key, default), default)
            
            # APIキープロパティに直接モック値を設定
            helper = OpenAIGitHelper()
            helper.api_key = 'test-api-key'  # 確実にモック値を設定
            
            yield helper
    
    def test_init(self, openai_helper):
        """初期化が正しく行われるかテスト"""
        assert openai_helper.use_openai is True
        assert openai_helper.api_key == 'test-api-key'
        assert openai_helper.model == 'gpt-3.5-turbo'
    
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._call_openai_api')
    def test_generate_commit_message(self, mock_call_api, openai_helper, setup_git_repo):
        """コミットメッセージ生成機能をテスト"""
        repo_path = setup_git_repo
        
        # テスト用の変更を加える
        test_file = Path(repo_path) / "test.py"
        with open(test_file, 'a', encoding='utf-8') as f:
            f.write('\n\ndef goodbye():\n    print("Goodbye!")\n')
        
        # 変更をステージングエリアに追加（これが必要）
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # APIからの返答をモック
        mock_call_api.return_value = "テスト関数の追加"
        
        # _run_git_commandもモックしてdiffの出力を制御
        with patch.object(openai_helper, '_run_git_command') as mock_run_command:
            # diffとfilesのモック結果を設定
            def mock_side_effect(cmd, cwd=None):
                if '--staged' in cmd and '--name-only' in cmd:
                    return MagicMock(stdout="test.py", returncode=0)
                elif '--staged' in cmd:
                    return MagicMock(stdout="@@ -1,4 +1,8 @@\n def hello():\n     print(\"Hello, World!\")\n \n+\n+def goodbye():\n+    print(\"Goodbye!\")\n+\n if __name__ == \"__main__\":\n     hello()", returncode=0)
                return MagicMock(stdout="", returncode=0)
            
            mock_run_command.side_effect = mock_side_effect
            
            # コミットメッセージを生成
            message = openai_helper.generate_commit_message(repo_path)
            
            # 検証
            assert message == "テスト関数の追加"
            mock_call_api.assert_called_once()
    
    @patch('requests.get')
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._call_openai_api')
    def test_analyze_pull_request(self, mock_call_api, mock_requests_get, openai_helper):
        """PRの分析機能をテスト"""
        # GitHub APIのレスポンスをモック
        mock_pr_response = MagicMock()
        mock_pr_response.raise_for_status = MagicMock()
        mock_pr_response.json.return_value = {
            'title': 'テストPR',
            'body': 'テスト用のPR説明',
            'changed_files': 2,
            'additions': 10,
            'deletions': 5,
            'user': {'login': 'test_user'}
        }
        
        mock_diff_response = MagicMock()
        mock_diff_response.raise_for_status = MagicMock()
        mock_diff_response.text = "@@ -1,4 +1,8 @@\n def hello():\n     print(\"Hello, World!\")\n \n+\n+def goodbye():\n+    print(\"Goodbye!\")\n+\n if __name__ == \"__main__\":\n     hello()"
        
        # requestsのget関数の動作を設定
        mock_requests_get.side_effect = lambda url, headers: mock_pr_response if 'diff' not in headers.get('Accept', '') else mock_diff_response
        
        # OpenAI APIの返答をモック
        mock_call_api.return_value = """
        # 概要
        テスト関数を追加するPRです。

        # リスク
        - エラーハンドリングがない
        - テストコードがない

        # 提案
        - エラーハンドリングを追加すべき
        - テストを書くべき
        """
        
        # PRを分析
        result = openai_helper.analyze_pull_request("https://github.com/user/repo/pull/123")
        
        # 検証
        assert 'テスト関数を追加する' in result['summary']
        assert len(result['risks']) > 0
        assert len(result['suggestions']) > 0
        mock_call_api.assert_called_once()
    
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._call_openai_api')
    def test_analyze_code_quality(self, mock_call_api, openai_helper, setup_git_repo):
        """コード品質分析機能をテスト"""
        repo_path = setup_git_repo
        file_path = Path(repo_path) / "test.py"
        
        # APIからの返答をモック
        mock_call_api.return_value = """
        # 概要
        シンプルで基本的なコードです。改善の余地があります。

        # 問題点
        - 関数のドキュメント文字列がありません
        - エラーハンドリングがありません

        # 改善案
        - docstringを追加する
        - 例外処理を追加する
        - テスト関数を実装する
        """
        
        # _extract_list_itemsをパッチして正しい形式のリストを返すようにする
        with patch.object(openai_helper, '_extract_list_items') as mock_extract:
            mock_extract.side_effect = lambda text: ["問題点1", "問題点2"] if "問題点" in text else ["改善案1", "改善案2", "改善案3"]
            
            # コード品質を分析
            result = openai_helper.analyze_code_quality(str(file_path))
        
        # 検証
        assert '概要' in result['summary']
        assert len(result['issues']) == 2
        assert len(result['suggestions']) == 3
        mock_call_api.assert_called_once()
    
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._call_openai_api')
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._run_git_command')
    def test_check_sensitive_info(self, mock_run_command, mock_call_api, openai_helper, setup_git_repo):
        """機密情報チェック機能をテスト"""
        repo_path = setup_git_repo
        
        # テスト用の変更を加える（機密情報を含む）
        secrets_file = Path(repo_path) / "secrets.py"
        with open(secrets_file, 'w', encoding='utf-8') as f:
            f.write('# 機密情報\nAPI_KEY = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"\n')
            f.write('PASSWORD = "supersecretpassword123"\n')
        
        # Gitコマンドの実行結果をモック
        mock_run_command.side_effect = lambda cmd, cwd=None, shell=False: MagicMock(
            stdout="secrets.py" if "--name-only" in cmd else "diff内容",
            returncode=0
        )
        
        # OpenAI APIの返答をモック
        mock_call_api.return_value = "分析した結果、いくつかの機密情報が見つかりました。4行目にAPIキー、5行目にパスワードが含まれています。"
        
        # ファイル読み込みをパッチして、正しく読み込めるようにする
        with patch('builtins.open') as mock_open:
            # ファイルの読み込み内容をモック
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = '# 機密情報\nAPI_KEY = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"\nPASSWORD = "supersecretpassword123"\n'
            mock_open.return_value = mock_file
            
            # 機密情報をチェック
            result = openai_helper.check_sensitive_info(repo_path)
        
        # 検証
        assert result['safe'] is False
        assert len(result['issues']) > 0
        assert any('APIキー' in issue['type'] for issue in result['issues']) or 'APIキー' in result['ai_analysis']
        mock_call_api.assert_called_once()
    
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._call_openai_api')
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._run_git_command')
    def test_execute_ai_git_command_commit(self, mock_run_command, mock_call_api, openai_helper, setup_git_repo):
        """AI生成コミットメッセージの実行をテスト"""
        repo_path = setup_git_repo
        
        # Gitコマンドの実行結果をモック
        def mock_side_effect(cmd, cwd=None):
            if 'status' in cmd:
                return MagicMock(stdout="M test.py", returncode=0)
            elif '--staged' in cmd and '--name-only' in cmd:
                return MagicMock(stdout="test.py", returncode=0)
            elif '--staged' in cmd:
                return MagicMock(stdout="@@ -1,4 +1,8 @@\n変更内容", returncode=0)
            elif 'commit' in cmd:
                return MagicMock(stdout="[main abc1234] AIが生成したコミットメッセージ", returncode=0)
            return MagicMock(stdout="", returncode=0)
        
        mock_run_command.side_effect = mock_side_effect
        
        # OpenAI APIの返答をモック
        mock_call_api.return_value = "AIが生成したコミットメッセージ"
        
        # AI生成コミットを実行
        result = openai_helper.execute_ai_git_command('ai-commit', repo_path)
        
        # 検証
        assert result['success'] is True
        assert 'AIが生成したコミットメッセージ' in result['message']
        mock_call_api.assert_called_once()


if __name__ == "__main__":
    pytest.main(['-v', __file__]) 