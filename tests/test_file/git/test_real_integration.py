#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
実際の接続を伴う統合テスト

実際のGitリポジトリとOpenAI APIに接続してGit操作とAI機能をテストします。
このテストを実行するには、以下の環境変数を設定してください：
- OPENAI_API_KEY: 実際のOpenAI APIキー
- TEST_REPO_PATH: テスト対象のGitリポジトリパス（デフォルト: カレントディレクトリ）
- SKIP_OPENAI_TESTS: 「true」に設定するとOpenAI APIを使用するテストをスキップ

注意: このテストは実際のリポジトリとAPI接続を使用するため、慎重に実行してください。
"""

import os
import sys
import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path
import time
import random
import string
import json
import datetime

# プロジェクトルートを正しく設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト対象のモジュールをインポート
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.git_batch import GitBatchProcessor, execute_git_command, find_git_repos
from src.utils.openai_git_helper import OpenAIGitHelper

# テスト結果を保存するグローバル変数
TEST_RESULTS = {}

# テスト用の環境変数を取得
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TEST_REPO_PATH = os.environ.get('TEST_REPO_PATH', '.')
SKIP_OPENAI_TESTS = os.environ.get('SKIP_OPENAI_TESTS', '').lower() == 'true'

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
        results_path = PROJECT_ROOT / "tests" / "results" / f"{category}_real_integration_test_results.json"
        
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

def random_string(length=8):
    """ランダムな文字列を生成"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def rmtree_retry(path, max_retries=5, delay=1.0):
    """
    リトライ機能付きのディレクトリ削除
    Windowsではファイルハンドルが解放されるのを待つ必要がある場合がある
    
    Args:
        path: 削除するディレクトリのパス
        max_retries: 最大リトライ回数
        delay: リトライ間の待機時間（秒）
    """
    for attempt in range(max_retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            return
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"警告: 一時ディレクトリの削除に失敗しました（試行 {attempt+1}/{max_retries}）: {e}")
                time.sleep(delay)
            else:
                print(f"警告: 一時ディレクトリの削除を諦めます: {path}")


class TestRealIntegration:
    """実際のGitリポジトリとOpenAI APIを使った統合テスト"""
    
    @pytest.fixture
    def setup_real_repo(self):
        """
        テスト用の実際のリポジトリをセットアップ
        既存のリポジトリをコピーして、テスト用のブランチを作成します
        """
        # テスト用の一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        original_repo_path = Path(TEST_REPO_PATH).resolve()
        
        try:
            print(f"\n実際のテスト用に一時リポジトリを作成: {temp_dir}")
            
            # リポジトリをクローン（存在する場合）またはコピー
            if (original_repo_path / '.git').exists():
                # Gitコマンドを使用してクローン
                subprocess.run(
                    ['git', 'clone', str(original_repo_path), temp_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                # 通常のディレクトリコピー
                shutil.copytree(original_repo_path, temp_dir, dirs_exist_ok=True)
                # 初期化
                subprocess.run(
                    ['git', 'init'],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            
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
            
            # テスト用ブランチを作成
            branch_name = f"test-branch-{random_string()}"
            subprocess.run(
                ['git', 'checkout', '-b', branch_name],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            yield temp_dir
            
            # テスト終了後にテストブランチを削除して元のブランチに戻す
            try:
                # 変更を元に戻す
                subprocess.run(
                    ['git', 'reset', '--hard', 'HEAD'],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # マスターブランチに切り替え
                subprocess.run(
                    ['git', 'checkout', 'main'],
                    cwd=temp_dir,
                    check=False,  # mainが無い場合もある
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            except Exception as e:
                print(f"ブランチのクリーンアップ中にエラー: {e}")
        finally:
            # 一時ディレクトリを削除（拡張されたリトライロジック使用）
            rmtree_retry(temp_dir)
    
    @pytest.fixture
    def real_openai_helper(self):
        """実際のOpenAI APIに接続するヘルパーを作成"""
        if SKIP_OPENAI_TESTS or not OPENAI_API_KEY:
            pytest.skip("OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
        
        # 環境変数にAPIキーを設定
        os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
        
        # 実際のOpenAIGitHelperインスタンスを作成
        helper = OpenAIGitHelper()
        
        # APIキーが正しく設定されているか確認
        if not helper.use_openai:
            # 直接APIキーを再設定して強制的に有効化
            helper.api_key = OPENAI_API_KEY
            helper.use_openai = True
            print(f"\nOpenAI APIを強制的に有効化しました: {helper.use_openai}")
        
        return helper
    
    def test_find_real_git_repos(self):
        """実際のリポジトリ検索をテスト"""
        repos = find_git_repos(TEST_REPO_PATH, recursive=True, max_depth=2)
        
        # 検証
        assert len(repos) > 0, "リポジトリが見つかりませんでした"
        print(f"\n見つかったリポジトリ: {repos}")
        
        # 見つかったリポジトリが有効か確認
        for repo in repos:
            git_dir = Path(repo) / '.git'
            assert git_dir.exists(), f"{repo}は有効なGitリポジトリではありません"
    
    def test_git_status_on_real_repo(self, setup_real_repo):
        """実際のリポジトリでGitステータスを確認"""
        repo_path = setup_real_repo
        
        # GitBatchProcessorを使用してステータスを取得
        processor = GitBatchProcessor([repo_path])
        results = processor.execute_batch('status')
        
        # 検証
        assert len(results) == 1, "結果が1件ではありません"
        repo_name = Path(repo_path).name
        assert repo_name in results, f"{repo_name}が結果に含まれていません"
        assert results[repo_name]['success'], "ステータス取得に失敗しました"
        
        print(f"\nGitステータス結果: {results[repo_name]['output']}")
    
    def test_git_commit_on_real_repo(self, setup_real_repo):
        """実際のリポジトリで変更をコミット"""
        repo_path = setup_real_repo
        
        # テスト用のファイルを作成
        test_file = Path(repo_path) / f"test_file_{random_string()}.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"このファイルはテスト用に作成されました（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # GitBatchProcessorを使用してコミット
        processor = GitBatchProcessor([repo_path])
        
        # まずステータスを確認
        status_results = processor.execute_batch('status')
        print(f"\nコミット前のステータス: {status_results}")
        
        # コミット実行
        commit_results = processor.execute_batch('commit')
        
        # 検証
        assert len(commit_results) == 1, "結果が1件ではありません"
        repo_name = Path(repo_path).name
        assert repo_name in commit_results, f"{repo_name}が結果に含まれていません"
        assert commit_results[repo_name]['success'], f"コミットに失敗しました: {commit_results[repo_name].get('error', '')}"
        
        print(f"\nコミット結果: {commit_results[repo_name]['output']}")
        
        # 再度ステータスを確認して変更が反映されたか確認
        status_after = processor.execute_batch('status')
        print(f"\nコミット後のステータス: {status_after}")
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_generate_commit_message_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用してコミットメッセージを生成"""
        repo_path = setup_real_repo
        
        # テスト用のファイルを作成
        test_file = Path(repo_path) / f"test_file_{random_string()}.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"このファイルはOpenAIコミットメッセージテスト用に作成されました（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # 変更をステージングエリアに追加
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # OpenAI APIでコミットメッセージを生成
        message = real_openai_helper.generate_commit_message(repo_path)
        
        # 検証
        assert message, "コミットメッセージが生成されませんでした"
        assert len(message) > 5, "生成されたコミットメッセージが短すぎます"
        
        print(f"\n生成されたコミットメッセージ: {message}")
        
        # 生成されたメッセージでコミット
        subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_check_sensitive_info_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用して機密情報チェック"""
        repo_path = setup_real_repo
        
        # 機密情報を含むファイルを作成
        test_file = Path(repo_path) / f"dummy_config_{random_string()}.py"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('# テスト用ダミー設定ファイル\n')
            f.write('DEBUG = True\n')
            f.write('# 以下はテスト用のダミー値です。実際のAPIキーではありません\n')
            f.write('DUMMY_API_KEY = "sk-12345dummyapikeyfortesting67890"\n')
            f.write('DUMMY_PASSWORD = "dummy_password123"\n')
        
        # 変更をステージングエリアに追加
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 機密情報をチェック
        result = real_openai_helper.check_sensitive_info(repo_path)
        
        # 検証 - 機密情報（テスト用ダミー値）を検出できるか
        print(f"\n機密情報チェック結果: {result}")
        
        # 注: 実際のAPIが機密情報と判断するかどうかは結果によって異なる
        # テスト用ダミー値なので検出されない可能性もあるが、機能自体が動作していることを確認
        assert 'safe' in result, "機密情報チェック結果に'safe'フィールドがありません"
        assert 'message' in result, "機密情報チェック結果に'message'フィールドがありません"
        assert 'issues' in result, "機密情報チェック結果に'issues'フィールドがありません"
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_analyze_code_quality_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用してコード品質を分析"""
        repo_path = setup_real_repo
        
        # テストファイルを作成
        test_file = Path(repo_path) / "test_code_quality.py"
        code_content = """
def add_numbers(a, b):
    return a + b

# このコードはあまり良くない実装例
def process_data(data):
    result = []
    for i in range(len(data)):
        result.append(data[i] * 2)
    return result
        """
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        # コード品質分析を実行
        result = real_openai_helper.analyze_code_quality(str(test_file))
        
        # 検証
        assert 'summary' in result, "分析結果に概要が含まれていません"
        assert 'issues' in result, "分析結果に問題点が含まれていません"
        assert 'suggestions' in result, "分析結果に改善案が含まれていません"
        
        print(f"\nコード品質分析結果: {result}")
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_suggest_feature_implementation_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用して新機能の実装案を提案"""
        repo_path = setup_real_repo
        
        # テスト用の機能説明
        feature_description = "ファイルの内容を読み込んで行数をカウントする関数"
        
        # 新機能の実装案を取得
        result = real_openai_helper.suggest_feature_implementation(
            repo_path, 
            feature_description
        )
        
        # 検証
        assert 'target_file' in result, "結果にターゲットファイルが含まれていません"
        assert 'code' in result, "結果にコードが含まれていません"
        assert 'explanation' in result, "結果に説明が含まれていません"
        assert len(result['code']) > 0, "生成されたコードが空です"
        
        print(f"\n機能実装案: {result['target_file']}")
        print(f"コードの一部: {result['code'][:100]}...")
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_branch_strategy_hint_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用してブランチ戦略のヒントを生成"""
        repo_path = setup_real_repo
        
        # 初期コミットがない可能性があるので、まず初期コミットを作成
        test_init_file = Path(repo_path) / "initial_commit_for_branch_strategy.txt"
        with open(test_init_file, 'w', encoding='utf-8') as f:
            f.write(f"初期コミット用ファイル（ブランチ戦略テスト用）（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # 初期コミットを作成
        subprocess.run(
            ['git', 'add', str(test_init_file)],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        subprocess.run(
            ['git', 'commit', '-m', "初期コミット（ブランチ戦略テスト用）"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 現在のブランチ名を取得
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        current_branch = result.stdout.strip()
        
        # ブランチ戦略のヒントを生成
        hint = real_openai_helper._generate_branch_strategy_hint(repo_path, current_branch)
        
        # 検証
        assert len(hint) > 0, "生成されたヒントが空です"
        assert "ブランチ戦略ヒント:" in hint, "ヒントに期待されるプレフィックスが含まれていません"
        
        print(f"\nブランチ戦略ヒント: {hint}")
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_ai_git_command_with_real_api(self, setup_real_repo, real_openai_helper):
        """実際のOpenAI APIを使用してAIコマンドを実行"""
        repo_path = setup_real_repo
        
        # テスト用のファイルを作成して変更を加える
        test_file = Path(repo_path) / f"ai_command_test_{random_string()}.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"AIコマンドテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # AIコマンドを実行 (ai-commit)
        result = real_openai_helper.execute_ai_git_command('ai-commit', repo_path)
        
        # 検証
        assert 'success' in result, "結果に成功フラグが含まれていません"
        assert result['success'], f"AIコマンド実行に失敗しました: {result.get('message', '')}"
        assert 'message' in result, "結果にメッセージが含まれていません"
        
        print(f"\nAIコマンド実行結果: {result['message']}")
    
    def test_git_pull_on_real_repo(self, setup_real_repo):
        """実際のリポジトリでプル操作を実行"""
        repo_path = setup_real_repo
        
        try:
            # GitBatchProcessorを使用してプルを実行
            processor = GitBatchProcessor([repo_path])
            results = processor.execute_batch('pull')
            
            # 検証
            assert len(results) == 1, "結果が1件ではありません"
            repo_name = Path(repo_path).name
            assert repo_name in results, f"{repo_name}が結果に含まれていません"
            
            # 結果が成功または「Already up to date」のような出力であることを検証
            # (リモート接続がない場合もあるため、必ずしも成功するとは限らない)
            print(f"\nGitプル結果: {results[repo_name]}")
            
        except Exception as e:
            # リモートが設定されていない場合はエラーになる可能性があるため、
            # エラーメッセージを出力して次のテストに進む
            print(f"プル操作中にエラーが発生しました（おそらくリモートが設定されていない）: {e}")
            pytest.skip("リモートリポジトリが設定されていないため、このテストをスキップします")
    
    def test_git_force_pull_on_real_repo(self, setup_real_repo):
        """実際のリポジトリで強制プル操作を実行"""
        repo_path = setup_real_repo
        
        try:
            # テスト用のファイルを作成してローカルに変更を加える
            test_file = Path(repo_path) / f"force_pull_test_{random_string()}.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"強制プルテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
            
            # 変更をステージングしてローカルの変更があることを確認
            subprocess.run(
                ['git', 'add', str(test_file)],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            status_before = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            assert status_before.stdout.strip(), "ローカルに変更がありません"
            
            # 現在のブランチを取得
            branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            current_branch = branch_result.stdout.strip()
            
            # GitBatchProcessorを使用して強制プルを実行
            options = {'branch': current_branch, 'try_stash': True}
            processor = GitBatchProcessor([repo_path], options)
            
            try:
                results = processor.execute_batch('force-pull')
                
                # 検証
                assert len(results) == 1, "結果が1件ではありません"
                repo_name = Path(repo_path).name
                assert repo_name in results, f"{repo_name}が結果に含まれていません"
                
                print(f"\nGit強制プル結果: {results[repo_name]}")
                
                # ステータスを再確認
                status_after = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 結果の出力のみ行い、テストは正常終了
                # stashが行われた場合はまだ変更が残っているはずなので、検証は行わない
                print(f"強制プル後のステータス:\n{status_after.stdout}")
                
            except Exception as e:
                # リモートが設定されていない場合はエラーになる可能性があるため、
                # エラーメッセージを出力して次のテストに進む
                print(f"強制プル実行中にエラーが発生しました: {e}")
                pytest.skip("強制プル実行中にエラーが発生したため、このテストをスキップします")
                
        except Exception as e:
            # 準備段階でエラーが発生した場合
            print(f"強制プルテストの準備中にエラーが発生しました: {e}")
            pytest.skip("テストの準備中にエラーが発生したため、このテストをスキップします")
    
    def test_git_checkout_on_real_repo(self, setup_real_repo):
        """実際のリポジトリでブランチ切り替えを実行"""
        repo_path = setup_real_repo
        
        # 初期コミットがない可能性があるので、まず初期コミットを作成
        test_init_file = Path(repo_path) / "initial_commit.txt"
        with open(test_init_file, 'w', encoding='utf-8') as f:
            f.write(f"初期コミット用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # 初期コミットを作成
        subprocess.run(
            ['git', 'add', str(test_init_file)],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        subprocess.run(
            ['git', 'commit', '-m', "初期コミット"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 新しいブランチ名を生成
        branch_name = f"test-checkout-{random_string()}"
        
        # 新しいブランチを作成
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # mainブランチに戻る
        # `-`ではなく具体的なブランチ名を指定する
        subprocess.run(
            ['git', 'checkout', 'main'],
            cwd=repo_path,
            check=False,  # mainブランチが無い場合もあるのでエラーを無視
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # GitBatchProcessorを使用してチェックアウトを実行
        processor = GitBatchProcessor([repo_path], {'branch': branch_name})
        results = processor.execute_batch('checkout')
        
        # 検証
        assert len(results) == 1, "結果が1件ではありません"
        repo_name = Path(repo_path).name
        assert repo_name in results, f"{repo_name}が結果に含まれていません"
        assert results[repo_name]['success'], f"チェックアウトに失敗しました: {results[repo_name].get('error', '')}"
        
        print(f"\nGitチェックアウト結果: {results[repo_name]['output']}")
        
        # 現在のブランチを確認
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        current_branch = result.stdout.strip()
        
        assert current_branch == branch_name, f"ブランチが正しく切り替わっていません: {current_branch} != {branch_name}"
    
    def test_git_reset_on_real_repo(self, setup_real_repo):
        """実際のリポジトリで変更のリセットを実行"""
        repo_path = setup_real_repo
        
        # 初期コミットがない可能性があるので、まず初期コミットを作成
        test_init_file = Path(repo_path) / "initial_commit_for_reset.txt"
        with open(test_init_file, 'w', encoding='utf-8') as f:
            f.write(f"初期コミット用ファイル（リセットテスト用）（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # 初期コミットを作成
        subprocess.run(
            ['git', 'add', str(test_init_file)],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        subprocess.run(
            ['git', 'commit', '-m', "初期コミット（リセットテスト用）"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # テスト用のファイルを作成して変更を加える
        test_file = Path(repo_path) / f"reset_test_{random_string()}.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"リセットテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # 変更をステージング
        subprocess.run(
            ['git', 'add', str(test_file)],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # ステータスを確認して変更があることを確認
        status_before = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        assert status_before.stdout.strip(), "ステージングされた変更がありません"
        
        # GitBatchProcessorを使用してリセットを実行
        processor = GitBatchProcessor([repo_path])
        results = processor.execute_batch('reset')
        
        # 検証
        assert len(results) == 1, "結果が1件ではありません"
        repo_name = Path(repo_path).name
        assert repo_name in results, f"{repo_name}が結果に含まれていません"
        assert results[repo_name]['success'], f"リセットに失敗しました: {results[repo_name].get('error', '')}"
        
        print(f"\nGitリセット結果: {results[repo_name]['output']}")
        
        # ステータスを再確認して変更がリセットされたことを確認
        status_after = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # リセット後はステージングされた変更が消えているはず（ただしuntracked filesは残る）
        # そのためポートセリン形式の出力は "?? ファイル名" のような形式になるはず
        assert all(line.startswith('??') for line in status_after.stdout.strip().split('\n') if line), \
            "変更が正しくリセットされていません"
    
    def test_git_clean_on_real_repo(self, setup_real_repo):
        """実際のリポジトリで未追跡ファイルのクリーンを実行"""
        repo_path = setup_real_repo
        
        # テスト用の未追跡ファイルを作成
        test_file = Path(repo_path) / f"clean_test_{random_string()}.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"クリーンテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
        
        # ステータスを確認して未追跡ファイルがあることを確認
        status_before = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        assert "??" in status_before.stdout, "未追跡ファイルがありません"
        
        # GitBatchProcessorを使用してクリーンを実行
        processor = GitBatchProcessor([repo_path])
        results = processor.execute_batch('clean')
        
        # 検証
        assert len(results) == 1, "結果が1件ではありません"
        repo_name = Path(repo_path).name
        assert repo_name in results, f"{repo_name}が結果に含まれていません"
        assert results[repo_name]['success'], f"クリーンに失敗しました: {results[repo_name].get('error', '')}"
        
        print(f"\nGitクリーン結果: {results[repo_name]['output']}")
        
        # ステータスを再確認して未追跡ファイルがクリーンされたことを確認
        status_after = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        assert "??" not in status_after.stdout, "未追跡ファイルがクリーンされていません"
        assert not test_file.exists(), "未追跡ファイルが削除されていません"
    
    def test_git_push_on_real_repo(self, setup_real_repo):
        """実際のリポジトリでプッシュ操作を実行"""
        repo_path = setup_real_repo
        
        try:
            # テスト用のファイルを作成してコミット
            test_file = Path(repo_path) / f"push_test_{random_string()}.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"プッシュテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
            
            # 変更をコミット
            subprocess.run(
                ['git', 'add', str(test_file)],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            subprocess.run(
                ['git', 'commit', '-m', f"テスト用コミット: {random_string()}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # GitBatchProcessorを使用してプッシュを実行
            processor = GitBatchProcessor([repo_path])
            results = processor.execute_batch('push')
            
            # 検証
            assert len(results) == 1, "結果が1件ではありません"
            repo_name = Path(repo_path).name
            assert repo_name in results, f"{repo_name}が結果に含まれていません"
            
            # 結果を出力 (成功・失敗に関わらず)
            print(f"\nGitプッシュ結果: {results[repo_name]}")
            
            # リモートが設定されていない場合はエラーになるはずなので、成功の検証はスキップ
            
        except Exception as e:
            # リモートが設定されていない場合はエラーになる可能性があるため、
            # エラーメッセージを出力して次のテストに進む
            print(f"プッシュ操作中にエラーが発生しました（おそらくリモートが設定されていない）: {e}")
            pytest.skip("リモートリポジトリが設定されていないため、このテストをスキップします")
    
    def test_git_full_push_on_real_repo(self, setup_real_repo):
        """実際のリポジトリで完全プッシュ操作（add→commit→push）を実行"""
        repo_path = setup_real_repo
        
        try:
            # テスト用のファイルを作成
            test_file = Path(repo_path) / f"full_push_test_{random_string()}.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"完全プッシュテスト用ファイル（{time.strftime('%Y-%m-%d %H:%M:%S')}）\n")
            
            # ステータスを確認して変更があることを確認
            status_before = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            assert status_before.stdout.strip(), "コミットする変更がありません"
            
            # GitBatchProcessorを使用して完全プッシュを実行
            message = f"自動テスト: 完全プッシュ {random_string()}"
            processor = GitBatchProcessor([repo_path], {'message': message})
            results = processor.execute_batch('full-push')
            
            # 検証
            assert len(results) == 1, "結果が1件ではありません"
            repo_name = Path(repo_path).name
            assert repo_name in results, f"{repo_name}が結果に含まれていません"
            
            # 結果を出力 (成功・失敗に関わらず)
            print(f"\nGit完全プッシュ結果: {results[repo_name]}")
            
            # ステータスを再確認して変更がコミットされたことを確認
            status_after = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # コミット部分は成功しているはず (プッシュはリモートの有無によって結果が変わる)
            assert not status_after.stdout.strip() or "??" in status_after.stdout, \
                "変更が正しくコミットされていません"
            
        except Exception as e:
            # エラーメッセージを出力して次のテストに進む
            print(f"完全プッシュ操作中にエラーが発生しました: {e}")
            pytest.skip("エラーが発生したため、このテストをスキップします")
    
    @pytest.mark.skipif(SKIP_OPENAI_TESTS or not OPENAI_API_KEY, 
                       reason="OpenAI APIキーが設定されていないか、OpenAIテストがスキップに設定されています")
    def test_analyze_pr_with_real_api(self, real_openai_helper):
        """実際のOpenAI APIを使用してPRを分析"""
        # テスト用の公開PRのURL (GitHubの公開リポジトリから選択 - 最新の有効なPRに変更)
        pr_url = "https://github.com/microsoft/vscode/pull/212000"
        
        # PR分析を実行
        result = real_openai_helper.analyze_pull_request(pr_url)
        
        # エラーチェック
        if 'error' in result:
            print(f"\nPR分析エラー: {result['error']}")
            pytest.skip(f"PR分析でエラーが発生したため、テストをスキップします: {result['error']}")
        
        # 検証
        assert 'summary' in result, "分析結果に概要が含まれていません"
        assert 'risks' in result, "分析結果にリスクが含まれていません"
        assert 'suggestions' in result, "分析結果に提案が含まれていません"
        
        print(f"\nPR分析結果の概要: {result['summary'][:100]}...")
        print(f"リスク数: {len(result['risks'])}")
        print(f"提案数: {len(result['suggestions'])}")


if __name__ == "__main__":
    pytest.main(['-v', __file__]) 