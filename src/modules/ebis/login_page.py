#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ad Ebis ログインページ操作モジュール

このモジュールは、Ad Ebisの管理画面へのログイン処理を行います。
シンプルに環境変数から認証情報を取得し、ログインフォームに入力します。
"""
import logging
import selectors
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from typing import Optional, Dict, Any

# 環境変数操作のためのユーティリティをインポート
from src.utils.environment import env
from ..selenium.browser import Browser
from ..selenium.login_page import LoginError

logger = logging.getLogger(__name__)

def login(browser: Browser, account_key: Optional[str] = None, username: Optional[str] = None, 
          password: Optional[str] = None) -> bool:
    """
    Ad Ebisにログインする
    
    Args:
        browser: ブラウザインスタンス
        account_key: アカウントキー（指定しない場合は環境変数から取得）
        username: ユーザー名（指定しない場合は環境変数から取得）
        password: パスワード（指定しない場合は環境変数から取得）
        
    Returns:
        bool: ログイン成功時はTrue、失敗時はFalse
        
    Raises:
        LoginError: ログインに失敗した場合
    """
    try:
        # 認証情報の取得
        account_key = account_key or env.get_env_var("EBIS_ACCOUNT_KEY")
        username = username or env.get_env_var("EBIS_USERNAME")
        password = password or env.get_env_var("EBIS_PASSWORD")
        
        if not all([account_key, username, password]):
            raise LoginError("認証情報が不足しています")
            
        # ログインページに移動
        login_url = env.get_config_value("LOGIN", "url")
        if not browser.navigate_to(login_url):
            raise LoginError("ログインページへの移動に失敗しました")
            
        # アカウントキーの入力
        account_key_element = browser.wait_for_element(("login", "account_key"), visible=True)
        if not account_key_element:
            raise LoginError("アカウントキー入力欄が見つかりません")
        account_key_element.clear()
        account_key_element.send_keys(account_key)
        
        # ユーザー名の入力
        username_element = browser.wait_for_element(("login", "username"), visible=True)
        if not username_element:
            raise LoginError("ユーザー名入力欄が見つかりません")
        username_element.clear()
        username_element.send_keys(username)
        
        # パスワードの入力
        password_element = browser.wait_for_element(("login", "password"), visible=True)
        if not password_element:
            raise LoginError("パスワード入力欄が見つかりません")
        password_element.clear()
        password_element.send_keys(password)
        
        # ログインボタンのクリック
        login_button = browser.wait_for_element(("login", "login_button"), visible=True)
        if not login_button:
            raise LoginError("ログインボタンが見つかりません")
            
        # クリック前のスクリーンショット
        browser.save_screenshot("before_login_click")
        
        # クリック操作の実行
        try:
            login_button.click()
        except Exception as click_error:
            logger.warning(f"通常のクリックに失敗: {click_error}")
            browser.driver.execute_script("arguments[0].click();", login_button)
            
        # ログイン成功の確認
        success_url = env.get_config_value("LOGIN", "success_url")
        redirect_timeout = int(env.get_config_value("LOGIN", "redirect_timeout", "10"))
        
        try:
            # リダイレクト完了を待機
            WebDriverWait(browser.driver, redirect_timeout).until(
                EC.url_contains(success_url)
            )
            logger.info("ログインに成功しました")
            
            # ログイン後のポップアップ処理
            handle_post_login_notices(browser)
            
            return True
            
        except TimeoutException:
            logger.error("ログイン後のリダイレクトがタイムアウトしました")
            browser.save_screenshot("error_login_redirect_timeout")
            raise LoginError("ログイン後のリダイレクトに失敗しました")
            
    except Exception as e:
        logger.error(f"ログイン中にエラーが発生しました: {str(e)}")
        browser.save_screenshot("error_login")
        raise LoginError(f"ログインに失敗しました: {str(e)}")

def retry_login(browser: Browser, max_attempts: int = 2, retry_interval: int = 5) -> bool:
    """
    ログインを指定回数リトライする
    
    Args:
        browser: ブラウザインスタンス
        max_attempts: 最大試行回数
        retry_interval: リトライ間隔（秒）
        
    Returns:
        bool: 最終的なログイン結果
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            if login(browser):
                return True
        except LoginError as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(f"ログインが{max_attempts}回失敗しました")
                raise
            logger.warning(f"ログイン失敗（{attempt}/{max_attempts}）: {str(e)}")
            time.sleep(retry_interval)
    return False

def handle_post_login_notices(browser: Browser) -> bool:
    """
    ログイン後のお知らせやポップアップを処理する
    
    Args:
        browser: ブラウザインスタンス
        
    Returns:
        bool: 処理成功時はTrue、ポップアップが無いか処理失敗時はFalse
    """
    try:
        logger.info("ログイン後のポップアップを確認しています...")
        time.sleep(1)  # ポップアップの表示を待機
        
        # ポップアップが表示されている場合は処理を行う
        try:
            try:
                popup_selector = selectors.get_selector("common_selectors", "popup_closebutton")
            except Exception as e:
                logger.debug(f"セレクタが見つかりません: {e}")
                return False
            
            # ポップアップ要素の検出と処理
            popup_element = browser.wait_for_element(
                (By.XPATH, popup_selector["selector_value"]),
                timeout=10,
                visible=True
            )
            
            if popup_element and popup_element.is_displayed():
                logger.info("ポップアップを検出しました")
                browser.save_screenshot("popup_detected")
                
                # クリックを試みる
                try:
                    popup_element.click()
                    logger.info("ポップアップを閉じました")
                    return True
                except Exception as click_error:
                    logger.debug(f"通常のクリックに失敗: {click_error}")
                    # JavaScriptでのクリックを試みる
                    browser.driver.execute_script("arguments[0].click();", popup_element)
                    logger.info("JavaScriptでポップアップを閉じました")
                    return True
                    
        except Exception as e:
            logger.debug(f"ポップアップ要素の検出に失敗: {e}")
            # ESCキーでの閉じる処理を試みる
            try:
                from selenium.webdriver.common.keys import Keys
                browser.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                logger.info("ESCキーでポップアップを閉じました")
                return True
            except Exception as ke:
                logger.debug(f"ESCキー送信に失敗: {ke}")
        
        logger.info("ポップアップは検出されませんでした")
        return False
        
    except Exception as e:
        logger.debug(f"ポップアップ処理中にエラーが発生しました（無視）: {e}")
        return False

# 後方互換性のためのクラス
class EbisLoginPage:
    """
    後方互換性のために残す簡易版のEbisLoginPageクラス
    
    内部では新しいlogin関数を使用します
    """
    def __init__(self, browser: Browser, logger_instance: Optional[logging.Logger] = None, 
                 config: Optional[Dict[str, Any]] = None):
        self.browser = browser
        self.logger = logger_instance or logger
        self.config = config or {}
        self.logger.info("EbisLoginPage を初期化しました。")
        
    def navigate_to_login_page(self, url: Optional[str] = None) -> bool:
        """ログインページに移動する（互換性のため）"""
        login_url = url or env.get_config_value('LOGIN', 'url', 'https://id.ebis.ne.jp/')
        self.logger.info(f"ログインページに移動します: {login_url}")
        return self.browser.navigate_to(login_url)
        
    def login(self, account_key: Optional[str] = None, username: Optional[str] = None, 
              password: Optional[str] = None, verify_success: bool = True) -> bool:
        """後方互換性のためのログインメソッド"""
        try:
            return login(self.browser, account_key, username, password)
        except LoginError as e:
            self.logger.error(str(e))
            return False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# --- テスト実行用の main ブロック ---
if __name__ == "__main__":
    import sys
    from src.utils.logging_config import setup_logging
    from src.utils.environment import env

    # 基本的なロギング設定
    setup_logging()
    main_logger = logging.getLogger("EbisLoginTest")

    # 環境変数のロード
    try:
        env.load_env()
        main_logger.info("環境変数をロードしました")
    except Exception as e:
        main_logger.error(f"環境変数のロードに失敗しました: {e}")
        sys.exit(1)

    # ブラウザ設定
    try:
        # ヘッドレスモードの設定
        headless = env.get_config_value("BROWSER", "headless", "false").lower() == "true"
        main_logger.info(f"ヘッドレスモード: {headless}")
        
        # ブラウザの初期化
        browser = Browser(
            headless=headless,
            logger=main_logger
        )
        
        # ブラウザのセットアップ
        if not browser.setup():
            main_logger.error("ブラウザのセットアップに失敗しました")
            sys.exit(1)
        
        # ログイン実行
        try:
            if retry_login(browser):
                main_logger.info("ログインに成功しました")
                # ログイン後の画面をキャプチャ
                browser.save_screenshot("login_success")
            else:
                main_logger.error("ログインに失敗しました")
                browser.save_screenshot("login_failed")
                sys.exit(1)
        except LoginError as e:
            main_logger.error(f"ログインエラー: {e}")
            sys.exit(1)
    
    except Exception as e:
        main_logger.error(f"予期せぬエラーが発生しました: {e}")
        sys.exit(1)
    
    finally:
        # ブラウザを終了
        if 'browser' in locals() and browser:
            browser.quit() 