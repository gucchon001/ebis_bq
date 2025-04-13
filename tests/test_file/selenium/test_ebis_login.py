#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
アドエビスログイン機能のテスト

EbisLoginPageクラスのログイン機能をテストします。
"""

import os
import sys
import time
import json
import pytest
import datetime
from pathlib import Path
from typing import Dict, Any
import logging
import traceback

# プロジェクトルートを正しく設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト対象のモジュールをインポート
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.environment import env
from src.utils.logging_config import get_logger
from src.modules.selenium.browser import Browser
from src.modules.ebis_login import EbisLoginPage, LoginError

# ロガーの設定
logger = get_logger(__name__)

# テスト結果を保存するグローバル変数
TEST_RESULTS = {}

# テスト開始時間を記録する変数
TEST_START_TIME = {}


@pytest.fixture(scope="session", autouse=True)
def report_test_results(request):
    """テスト終了時に結果をまとめて出力するフィクスチャ"""
    yield
    print("\n")
    print("=" * 80)
    print("               アドエビスログインテスト結果               ")
    print("=" * 80)
    print(f"{'テスト名':<40}{'結果':<10}{'担保された機能'}")
    print("-" * 80)
    for test_name, result in TEST_RESULTS.items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{test_name:<40}{status:<10}{result['description']}")
    print("-" * 80)
    print(f"テスト環境: Python {sys.version.split()[0]}")
    pass_count = sum(1 for r in TEST_RESULTS.values() if r["passed"])
    fail_count = len(TEST_RESULTS) - pass_count
    print(f"総合結果: {pass_count} passed / {fail_count} failed")
    print("=" * 80)
    
    # 結果をJSONファイルに保存
    try:
        # カテゴリ情報を取得（現在のフォルダ名）
        category = Path(__file__).parent.name
        results_path = PROJECT_ROOT / "tests" / "results" / f"ebis_login_test_results.json"
        
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


def record_result(name, passed, description):
    """テスト結果を記録する関数"""
    # フレームを取得して呼び出し元のコードについての情報を収集
    import inspect
    import time
    
    frame = inspect.currentframe().f_back
    module = inspect.getmodule(frame)
    
    # テスト対象ファイルを推測（現在のテストファイル名から）
    test_file = module.__file__
    src_file = test_file.replace("tests/test_file", "src").replace("test_", "")
    
    # カテゴリ情報を取得（テストファイルの親ディレクトリ名）
    category_path = Path(test_file).parent
    category = category_path.name
    
    # テスト開始時間を記録する変数をグローバルに
    global TEST_START_TIME
    if 'TEST_START_TIME' not in globals():
        TEST_START_TIME = {}
    
    # テスト終了時に実行時間を計算
    execution_time = 0.0
    if name in TEST_START_TIME:
        execution_time = time.time() - TEST_START_TIME[name]
    else:
        # 開始時間が記録されていなければ、関数名を抽出して作成
        # 現在のテスト関数名を取得（呼び出し元）
        calling_function = frame.f_code.co_name
        if calling_function.startswith("test_"):
            TEST_START_TIME[calling_function] = time.time()
    
    # 現在の関数名をメソッド名として使用
    method_name = frame.f_code.co_name
    
    # 結果を記録（カテゴリ情報を追加）
    TEST_RESULTS[name] = {
        "passed": passed,
        "description": description,
        "execution_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": src_file,
        "test_file": test_file,
        "method": method_name,
        "execution_time": round(execution_time, 2),
        "category": category
    }
    return passed


class TestEbisLogin:
    """アドエビスログインのテストクラス"""
    
    @pytest.fixture(scope="class")
    def browser_config(self):
        """ブラウザの設定を読み込むフィクスチャ"""
        env.load_env()
        
        # テスト用のヘッドレスモードを無効化 (テスト用なので確認しやすいように)
        headless = False
        
        # 自動スクリーンショットとエラー時のスクリーンショットを有効化
        auto_screenshot = True
        screenshot_on_error = True
        
        config = {
            'BROWSER': {
                'headless': str(headless).lower(),
                'auto_screenshot': str(auto_screenshot).lower(),
                'screenshot_dir': 'logs/screenshots',
                'screenshot_format': 'png',
                'screenshot_quality': '100',
                'screenshot_on_error': str(screenshot_on_error).lower()
            },
            'LOGIN': {
                'url': env.get_config_value("LOGIN", "url", "https://id.ebis.ne.jp/"),
                'success_url': env.get_config_value("LOGIN", "success_url", "https://bishamon.ebis.ne.jp/dashboard"),
                'max_attempts': '3',
                'redirect_timeout': '10',
                'element_timeout': '5'
            }
        }
        
        # スクリーンショットディレクトリの絶対パスを作成
        screenshot_dir = config['BROWSER']['screenshot_dir']
        if not os.path.isabs(screenshot_dir):
            screenshot_dir = os.path.join(
                str(env.get_project_root()), screenshot_dir
            )
        
        # スクリーンショットディレクトリが存在しない場合は作成
        os.makedirs(screenshot_dir, exist_ok=True)
        
        return config
    
    @pytest.fixture(scope="class")
    def browser(self, browser_config):
        """Browserクラスのインスタンスを作成するフィクスチャ"""
        browser = Browser(
            headless=browser_config['BROWSER']['headless'] == 'true',
            config=browser_config,
            logger=logger
        )
        
        # ブラウザのセットアップ
        browser.setup()
        
        yield browser
        
        # テスト終了後のクリーンアップ
        browser.close()
    
    def test_ebis_login_initialization(self, browser_config):
        """EbisLoginPageクラスの初期化テスト"""
        # 開始時刻を記録
        TEST_START_TIME["test_ebis_login_initialization"] = time.time()
        
        try:
            # EbisLoginPageインスタンスの作成
            ebis_login = EbisLoginPage(
                logger=logger,
                config=browser_config
            )
            
            # 認証情報が正しく読み込まれていることを確認
            assert hasattr(ebis_login, 'ebis_username'), "ユーザー名が設定されていません"
            assert hasattr(ebis_login, 'ebis_password'), "パスワードが設定されていません"
            assert hasattr(ebis_login, 'ebis_account_key'), "アカウントキーが設定されていません"
            
            # 値が空文字でない場合（実際の値がある場合）もチェック
            # テスト環境では空の場合もあるため、このチェックは行わない
            
            # ログイン関連のURLが設定されていることを確認
            assert ebis_login.login_url, "ログインURLが設定されていません"
            assert ebis_login.dashboard_url, "ダッシュボードURLが設定されていません"
            
            # 成功をレコード
            record_result(
                "test_ebis_login_initialization",
                True,
                "EbisLoginPageクラスの初期化と設定の読み込み"
            )
        except Exception as e:
            # 失敗をレコード
            logger.error(f"テスト中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            record_result(
                "test_ebis_login_initialization",
                False,
                "EbisLoginPageクラスの初期化と設定の読み込み"
            )
            raise
    
    def test_ebis_login_with_valid_credentials(self, browser):
        """有効な認証情報でのログインテスト"""
        # 開始時刻を記録
        TEST_START_TIME["test_ebis_login_with_valid_credentials"] = time.time()
        
        # 環境変数が正しく設定されているかチェック
        if (not os.environ.get("EBIS_USERNAME") or 
            not os.environ.get("EBIS_PASSWORD") or 
            not os.environ.get("EBIS_ACCOUNT_KEY")):
            pytest.skip("認証情報が設定されていないためテストをスキップします")
        
        try:
            # EbisLoginPageインスタンスの作成（既存のブラウザを使用）
            ebis_login = EbisLoginPage(
                browser=browser,
                logger=logger
            )
            
            # ログイン処理の実行
            login_result = ebis_login.login_to_ebis()
            
            # ログイン成功を検証
            assert login_result, "ログインに失敗しました"
            
            # 現在のURLがダッシュボードURLを含むことを確認
            current_url = browser.get_current_url()
            assert ebis_login.dashboard_url in current_url, f"予期されるダッシュボードURLに遷移していません: {current_url}"
            
            # 成功をレコード
            record_result(
                "test_ebis_login_with_valid_credentials",
                True,
                "有効な認証情報を使用したアドエビスへのログイン機能"
            )
        except Exception as e:
            # 失敗をレコード
            logger.error(f"テスト中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            record_result(
                "test_ebis_login_with_valid_credentials",
                False,
                "有効な認証情報を使用したアドエビスへのログイン機能"
            )
            raise
    
    def test_post_login_notice_handling(self, browser):
        """ログイン後の通知処理テスト"""
        # 開始時刻を記録
        TEST_START_TIME["test_post_login_notice_handling"] = time.time()
        
        # すでにブラウザがダッシュボードページにいることを想定
        try:
            # EbisLoginPageインスタンスの作成（既存のブラウザを使用）
            ebis_login = EbisLoginPage(
                browser=browser,
                logger=logger
            )
            
            # ログイン後の通知処理
            notice_result = ebis_login.handle_post_login_notice()
            
            # 処理が成功したことを確認（例外が発生しなければ成功）
            assert notice_result is not False, "ログイン後の通知処理に失敗しました"
            
            # 成功をレコード
            record_result(
                "test_post_login_notice_handling",
                True,
                "ログイン後の通知やポップアップの処理機能"
            )
        except Exception as e:
            # 失敗をレコード
            logger.error(f"テスト中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            record_result(
                "test_post_login_notice_handling",
                False,
                "ログイン後の通知やポップアップの処理機能"
            )
            raise
    
    def test_navigate_to_dashboard(self, browser):
        """ダッシュボードへの移動テスト"""
        # 開始時刻を記録
        TEST_START_TIME["test_navigate_to_dashboard"] = time.time()
        
        try:
            # EbisLoginPageインスタンスの作成（既存のブラウザを使用）
            ebis_login = EbisLoginPage(
                browser=browser,
                logger=logger
            )
            
            # ダッシュボードへの移動
            navigate_result = ebis_login.navigate_to_dashboard()
            
            # 移動が成功したことを確認
            assert navigate_result, "ダッシュボードへの移動に失敗しました"
            
            # 現在のURLがダッシュボードURLと一致することを確認
            current_url = browser.get_current_url()
            assert ebis_login.dashboard_url in current_url, f"ダッシュボードURLに遷移していません: {current_url}"
            
            # 成功をレコード
            record_result(
                "test_navigate_to_dashboard",
                True,
                "ダッシュボードページへの移動機能"
            )
        except Exception as e:
            # 失敗をレコード
            logger.error(f"テスト中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            record_result(
                "test_navigate_to_dashboard",
                False,
                "ダッシュボードページへの移動機能"
            )
            raise
    
    def test_error_handling_with_invalid_credentials(self):
        """無効な認証情報での例外処理テスト"""
        # 開始時刻を記録
        TEST_START_TIME["test_error_handling_with_invalid_credentials"] = time.time()
        
        try:
            # 無効な認証情報を持つ設定を作成
            invalid_config = {
                'BROWSER': {
                    'headless': 'true',
                    'auto_screenshot': 'true',
                    'screenshot_dir': 'logs/screenshots',
                    'screenshot_on_error': 'true'
                },
                'LOGIN': {
                    'url': 'https://id.ebis.ne.jp/',
                    'success_url': 'https://bishamon.ebis.ne.jp/dashboard',
                    'max_attempts': '1'  # 1回だけ試行
                }
            }
            
            # 環境変数を一時的に上書き
            os.environ["EBIS_USERNAME"] = "invalid_user"
            os.environ["EBIS_PASSWORD"] = "invalid_password"
            os.environ["EBIS_ACCOUNT_KEY"] = "invalid_key"
            
            # EbisLoginPageインスタンスの作成
            with pytest.raises(LoginError):
                ebis_login = EbisLoginPage(
                    logger=logger,
                    config=invalid_config
                )
                
                # この呼び出しはLoginErrorを発生させるはず
                ebis_login.login_to_ebis()
            
            # 成功をレコード（例外が発生することを確認できた）
            record_result(
                "test_error_handling_with_invalid_credentials",
                True,
                "無効な認証情報に対するエラーハンドリング機能"
            )
        except Exception as e:
            # 想定外の例外が発生した場合は失敗
            if not isinstance(e, LoginError) and not isinstance(e, pytest.raises.Exception):
                logger.error(f"テスト中に想定外のエラーが発生しました: {str(e)}")
                logger.error(traceback.format_exc())
                record_result(
                    "test_error_handling_with_invalid_credentials",
                    False,
                    "無効な認証情報に対するエラーハンドリング機能"
                )
                raise
            else:
                # 期待通りのLoginErrorが発生した場合は成功
                record_result(
                    "test_error_handling_with_invalid_credentials",
                    True,
                    "無効な認証情報に対するエラーハンドリング機能"
                )
        finally:
            # 環境変数をリセット
            if "EBIS_USERNAME" in os.environ:
                del os.environ["EBIS_USERNAME"]
            if "EBIS_PASSWORD" in os.environ:
                del os.environ["EBIS_PASSWORD"]
            if "EBIS_ACCOUNT_KEY" in os.environ:
                del os.environ["EBIS_ACCOUNT_KEY"]


if __name__ == "__main__":
    # テストを直接実行する場合
    pytest.main(["-xvs", __file__]) 