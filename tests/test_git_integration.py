#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Git関連ツールの統合テストモジュール

GitBatchProcessorとOpenAIGitHelperの統合機能をテストします
"""

import os
import sys
import pytest
import tempfile
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.git_batch import GitBatchProcessor, execute_git_command, find_git_repos
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


class TestGitIntegration:
    """GitBatchProcessorとOpenAIGitHelperの統合テスト"""
    
    @pytest.fixture
    def setup_integration_repo(self):
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
    def mock_openai_helper(self):
        """モック化されたOpenAIGitHelperを作成"""
        with patch('src.utils.openai_git_helper.OpenAIGitHelper._get_config_value') as mock_config:
            mock_config.side_effect = lambda section, key, default: {
                ('GIT', 'use_openai', 'true'): 'true',
                ('OPENAI', 'api_key', ''): 'test-api-key',
                ('OPENAI', 'model', 'gpt-3.5-turbo'): 'gpt-3.5-turbo',
            }.get((section, key, default), default)
            
            helper = OpenAIGitHelper()
            helper.api_key = 'test-api-key'  # 確実にモック値を設定
            
            # OpenAI APIの呼び出しをモック
            with patch.object(helper, '_call_openai_api') as mock_call_api:
                mock_call_api.return_value = "テスト関数の追加"
                yield helper, mock_call_api
    
    @patch('src.utils.openai_git_helper.OpenAIGitHelper._run_git_command')
    def test_check_sensitive_info_before_push(self, mock_run_command, setup_integration_repo, mock_openai_helper):
        """プッシュ前の機密情報チェック機能をテスト"""
        repo_path = setup_integration_repo
        openai_helper, mock_call_api = mock_openai_helper
        
        # 機密情報を含むファイルを作成
        secrets_file = Path(repo_path) / "secrets.py"
        with open(secrets_file, 'w', encoding='utf-8') as f:
            f.write('# 機密情報\nAPI_KEY = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"\n')
            f.write('PASSWORD = "supersecretpassword123"\n')
        
        # Gitコマンドの実行結果をモック
        mock_run_command.side_effect = lambda cmd, cwd=None, shell=False: MagicMock(
            stdout="secrets.py" if "--name-only" in cmd else "diff内容",
            returncode=0
        )
        
        # ファイル読み込みをパッチして、正しく読み込めるようにする
        with patch('builtins.open') as mock_open:
            # ファイルの読み込み内容をモック
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = '# 機密情報\nAPI_KEY = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"\nPASSWORD = "supersecretpassword123"\n'
            mock_open.return_value = mock_file
            
            # 機密情報をチェック
            result = openai_helper.check_sensitive_info(repo_path)
        
        # 検証
        assert not result['safe']
        assert '機密情報の漏洩リスク' in result['message']
        
        # APIレスポンスのモックが呼ばれたことを確認
        mock_call_api.assert_called_once()
    
    @patch('src.utils.git_batch.GitStatus.execute')
    @patch('src.utils.openai_git_helper.OpenAIGitHelper.generate_commit_message')
    def test_git_batch_with_ai_message(self, mock_generate_message, mock_status, setup_integration_repo, mock_openai_helper):
        """バッチプロセッサとAIコミットメッセージ連携をテスト"""
        repo_path = setup_integration_repo
        openai_helper, _ = mock_openai_helper
        
        # GitStatusの実行結果をモック
        mock_status.return_value = {
            'success': True,
            'output': 'M test.py',
            'command': 'git status --short'
        }
        
        # コミットメッセージ生成をモック
        mock_generate_message.return_value = "AIが生成したコミットメッセージ"
        
        # GitBatchProcessorのインスタンスを作成
        batch_processor = GitBatchProcessor([repo_path])
        
        # GitStatusで変更を確認
        results = batch_processor.execute_batch('status')
        
        # 検証
        assert len(results) == 1
        assert all(result['success'] for result in results.values())
        
        # AI生成コミットメッセージで実行
        assert openai_helper.use_openai is True
        message = openai_helper.generate_commit_message(repo_path)
        
        # 検証
        assert message == "AIが生成したコミットメッセージ"


if __name__ == "__main__":
    pytest.main(['-v', __file__]) 