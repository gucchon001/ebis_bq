#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ポップアップハンドラーのテスト

JavaScriptのアラート、確認ダイアログ、プロンプトの処理をテストします。
また、モーダルダイアログやポップアップウィンドウの処理もテストします。
"""

import os
import sys
import time
import json
import pytest
import datetime
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# プロジェクトルートを正しく設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト対象のモジュールをインポート
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.environment import env
from src.utils.logging_config import get_logger
from src.modules.selenium.browser import Browser
from src.modules.selenium.popup_handler import PopupHandler

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
        results_path = PROJECT_ROOT / "tests" / "results" / f"{category}_popup_handler_test_results.json"
        
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
        "category": category  # カテゴリ情報を明示的に追加
    }
    return passed

class TestPopupHandler:
    """ポップアップ通知と警告ダイアログの処理テスト"""
    
    @pytest.fixture(scope="function")
    def browser(self):
        """Browserインスタンスのフィクスチャ"""
        # 環境変数と設定の読み込み
        env.load_env()
        
        # Browserインスタンスの作成
        headless_config = env.get_config_value("BROWSER", "headless", "true")
        headless = headless_config if isinstance(headless_config, bool) else headless_config.lower() == "true"
        
        browser = Browser(
            logger=logger,
            headless=headless,
            timeout=int(env.get_config_value("BROWSER", "timeout", "10"))
        )
        
        # ブラウザの初期化
        if not browser.setup():
            pytest.fail("ブラウザの初期化に失敗しました")
        
        yield browser
        
        # テスト終了後にブラウザを閉じる
        browser.quit()
    
    @pytest.fixture(scope="function")
    def login_page(self, browser):
        """LoginPageインスタンスのフィクスチャ"""
        # LoginPageインスタンスの作成
        login_page = LoginPage(
            browser=browser,
            logger=logger
        )
        
        yield login_page
    
    @pytest.fixture(scope="function")
    def popup_test_url(self):
        """ポップアップテスト用URL"""
        # テスト用のHTMLファイルのパスを取得
        project_root = env.get_project_root()
        popup_test_html = os.path.join(project_root, "tests", "data", "popup_test.html")
        
        # HTMLファイルが存在しない場合は、一時的に作成
        if not os.path.exists(popup_test_html):
            os.makedirs(os.path.dirname(popup_test_html), exist_ok=True)
            with open(popup_test_html, "w", encoding="utf-8") as f:
                f.write(self._create_popup_test_html())
        
        # file:// プロトコルでローカルHTMLへのURLを返す
        popup_url = f"file://{popup_test_html}"
        logger.info(f"ポップアップテスト用URL: {popup_url}")
        return popup_url
    
    def _create_popup_test_html(self):
        """ポップアップテスト用のHTMLを生成"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>ポップアップテスト</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                button { margin: 10px; padding: 5px 10px; }
                .popup { 
                    display: none; position: fixed; top: 50%; left: 50%; 
                    transform: translate(-50%, -50%); background: #fff;
                    border: 1px solid #ccc; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.3);
                    z-index: 100;
                }
                .overlay {
                    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.5); z-index: 50;
                }
                .cookie-notice {
                    position: fixed; bottom: 0; left: 0; right: 0; background: #f1f1f1;
                    padding: 10px; text-align: center; border-top: 1px solid #ddd;
                }
            </style>
        </head>
        <body>
            <h1>ポップアップテスト</h1>
            
            <h2>ブラウザダイアログテスト</h2>
            <button id="alertBtn">アラートを表示</button>
            <button id="confirmBtn">確認ダイアログを表示</button>
            <button id="promptBtn">プロンプトを表示</button>
            
            <h2>カスタムポップアップテスト</h2>
            <button id="modalBtn">モーダルを表示</button>
            <div id="result"></div>
            
            <div id="overlay" class="overlay"></div>
            <div id="modal" class="popup">
                <h3>ログイン成功</h3>
                <p>ようこそ、ユーザーさん！</p>
                <p>お知らせ：システムメンテナンスのお知らせ</p>
                <button id="closeModalBtn">閉じる</button>
            </div>
            
            <div id="cookieNotice" class="cookie-notice">
                <p>当サイトではCookieを使用しています。続行することで同意したことになります。</p>
                <button id="acceptCookieBtn">同意する</button>
            </div>
            
            <script>
                // アラートボタン
                document.getElementById('alertBtn').addEventListener('click', function() {
                    alert('これはアラートです。');
                });
                
                // 確認ダイアログボタン
                document.getElementById('confirmBtn').addEventListener('click', function() {
                    var result = confirm('続行しますか？');
                    document.getElementById('result').textContent = result ? '「OK」が選択されました' : '「キャンセル」が選択されました';
                });
                
                // プロンプトボタン
                document.getElementById('promptBtn').addEventListener('click', function() {
                    var name = prompt('お名前を入力してください：', '');
                    if (name) {
                        document.getElementById('result').textContent = 'こんにちは、' + name + 'さん！';
                    } else {
                        document.getElementById('result').textContent = 'キャンセルされました';
                    }
                });
                
                // モーダルボタン
                document.getElementById('modalBtn').addEventListener('click', function() {
                    document.getElementById('overlay').style.display = 'block';
                    document.getElementById('modal').style.display = 'block';
                });
                
                // モーダルを閉じるボタン
                document.getElementById('closeModalBtn').addEventListener('click', function() {
                    document.getElementById('overlay').style.display = 'none';
                    document.getElementById('modal').style.display = 'none';
                });
                
                // Cookie通知を閉じるボタン
                document.getElementById('acceptCookieBtn').addEventListener('click', function() {
                    document.getElementById('cookieNotice').style.display = 'none';
                });
            </script>
        </body>
        </html>
        """
    
    def test_detect_browser_alert(self, browser, popup_test_url):
        """ブラウザアラートの検出と処理テスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # アラートボタンをクリック
        alert_button = browser.find_element(By.ID, "alertBtn")
        alert_button.click()
        
        # アラートの検出
        alert_info = browser._check_alerts()
        assert alert_info['present'], "アラートが検出されませんでした"
        
        # アラートのテキスト確認
        assert "これはアラート" in alert_info.get('text', ''), "アラートのテキストが正しくありません"
        
        # アラートを受け入れる
        browser.driver.switch_to.alert.accept()
        logger.info("アラートを受け入れました")
        
        # アラートが閉じられたことを確認
        time.sleep(1)
        alert_info = browser._check_alerts()
        assert not alert_info['present'], "アラートが閉じられていません"
    
    def test_handle_confirm_dialog(self, browser, popup_test_url):
        """確認ダイアログの処理テスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # 確認ダイアログボタンをクリック
        confirm_button = browser.find_element(By.ID, "confirmBtn")
        confirm_button.click()
        
        # 確認ダイアログの検出
        alert_info = browser._check_alerts()
        assert alert_info['present'], "確認ダイアログが検出されませんでした"
        
        # ダイアログをキャンセル
        browser.driver.switch_to.alert.dismiss()
        logger.info("確認ダイアログをキャンセルしました")
        
        # 結果の確認
        time.sleep(1)
        result_element = browser.find_element(By.ID, "result")
        assert "キャンセル" in result_element.text, "確認ダイアログのキャンセル結果が正しくありません"
    
    def test_custom_popup_detection(self, browser, popup_test_url):
        """カスタムポップアップの検出テスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # モーダルボタンをクリック
        modal_button = browser.find_element(By.ID, "modalBtn")
        modal_button.click()
        
        # モーダルが表示されるまで待機
        try:
            modal = WebDriverWait(browser.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "modal"))
            )
            assert modal.is_displayed(), "モーダルが表示されていません"
            
            # モーダル内のテキストを確認
            modal_text = modal.text
            assert "ログイン成功" in modal_text, "モーダル内のテキストが正しくありません"
            assert "システムメンテナンス" in modal_text, "モーダル内のテキストが正しくありません"
            
            # モーダルを閉じる
            close_button = browser.find_element(By.ID, "closeModalBtn")
            close_button.click()
            
            # モーダルが閉じられたことを確認
            WebDriverWait(browser.driver, 5).until(
                EC.invisibility_of_element_located((By.ID, "modal"))
            )
            logger.info("モーダルが閉じられました")
            
        except TimeoutException:
            pytest.fail("モーダルの表示待機中にタイムアウトしました")
    
    def test_cookie_notice_handling(self, browser, popup_test_url):
        """Cookie通知の処理テスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # Cookie通知が表示されていることを確認
        cookie_notice = browser.find_element(By.ID, "cookieNotice")
        assert cookie_notice.is_displayed(), "Cookie通知が表示されていません"
        
        # 通知内のテキストを確認
        notice_text = cookie_notice.text
        assert "Cookieを使用しています" in notice_text, "Cookie通知のテキストが正しくありません"
        
        # 同意ボタンをクリック
        accept_button = browser.find_element(By.ID, "acceptCookieBtn")
        accept_button.click()
        
        # 通知が非表示になったことを確認
        time.sleep(1)
        assert not cookie_notice.is_displayed(), "Cookie通知が非表示になっていません"
        logger.info("Cookie通知を閉じました")
    
    def test_login_page_popup_detection(self, browser, login_page, popup_test_url):
        """ログインページでのポップアップ検出テスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # ログインページを初期化
        login_page.url = popup_test_url
        
        # モーダルボタンをクリック（ログイン成功をシミュレート）
        modal_button = browser.find_element(By.ID, "modalBtn")
        modal_button.click()
        
        # ログイン後の通知をチェック
        try:
            # モーダル要素を直接確認
            modal = browser.find_element(By.ID, "modal")
            assert modal.is_displayed(), "ログイン後のモーダルが表示されていません"
            
            # モーダルのテキストを確認
            modal_text = modal.text
            assert "ログイン成功" in modal_text, "ログイン成功メッセージが表示されていません"
            logger.info(f"ログイン後の通知を確認しました: {modal_text}")
            
            # テスト成功
            return
        except Exception as e:
            pytest.fail(f"ポップアップ検出中にエラーが発生しました: {str(e)}")
    
    def test_multiple_popups_handling(self, browser, popup_test_url):
        """複数のポップアップを連続して処理するテスト"""
        # テストページに移動
        browser.navigate_to(popup_test_url)
        
        # まずCookie通知を処理
        cookie_notice = browser.find_element(By.ID, "cookieNotice")
        accept_button = browser.find_element(By.ID, "acceptCookieBtn")
        accept_button.click()
        time.sleep(0.5)
        
        # 次にアラートを表示して処理
        alert_button = browser.find_element(By.ID, "alertBtn")
        alert_button.click()
        time.sleep(0.5)
        
        # アラートを処理
        browser.driver.switch_to.alert.accept()
        time.sleep(0.5)
        
        # 最後にモーダルを表示して処理
        modal_button = browser.find_element(By.ID, "modalBtn")
        modal_button.click()
        time.sleep(0.5)
        
        # モーダルを閉じる
        close_button = browser.find_element(By.ID, "closeModalBtn")
        close_button.click()
        time.sleep(0.5)
        
        # すべてのポップアップが閉じられていることを確認
        assert not cookie_notice.is_displayed(), "Cookie通知が非表示になっていません"
        
        alert_info = browser._check_alerts()
        assert not alert_info['present'], "アラートが閉じられていません"
        
        modal = browser.find_element(By.ID, "modal")
        assert not modal.is_displayed(), "モーダルが閉じられていません"
        
        logger.info("すべてのポップアップを正常に処理しました") 