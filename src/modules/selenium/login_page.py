#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汎用的なログインページ操作モジュール

様々なWebサイトのログイン処理を実行するための汎用的なクラスを提供します。
POMパターン（Page Object Model）で実装し、Browser クラスの機能を活用します。
"""

import os
import time
import sys
import functools
from pathlib import Path
import traceback
import urllib.parse
import re
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 相対インポートでBrowserクラスを取得
from .browser import Browser

# 環境変数操作用のユーティリティをインポート（存在する場合）
try:
    from src.utils.environment import env
    ENV_UTILS_AVAILABLE = True
except ImportError:
    ENV_UTILS_AVAILABLE = False

# カスタム例外クラス
class LoginError(Exception):
    """
    ログイン処理中に発生するエラーを表す例外クラス
    """
    pass

# エラーハンドリング用のデコレータ
def handle_errors(screenshot_name=None, raise_exception=False):
    """
    共通のエラーハンドリングを行うデコレータ
    
    Args:
        screenshot_name (str, optional): エラー時に保存するスクリーンショットの名前
        raise_exception (bool, optional): Trueの場合は例外を再発生させる
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                method_name = func.__name__
                error_msg = f"{method_name}の実行中にエラーが発生しました: {str(e)}"
                self.logger.error(error_msg)
                self.logger.error(traceback.format_exc())
                
                if hasattr(self, 'browser') and screenshot_name:
                    screenshot_file = f"{screenshot_name}_{int(time.time())}.png"
                    self.browser.save_screenshot(screenshot_file)
                
                if raise_exception:
                    raise
                return False
        return wrapper
    return decorator

class LoginPage:
    """
    汎用ログインページの操作を担当するクラス
    様々なWebサイトのログイン処理に対応できるよう設定から情報を読み込みます
    POMパターン（Page Object Model）で実装しつつ、Browser クラスの汎用機能を活用しています
    
    以下の特徴があります：
    1. セレクタをクラス変数として定義し、目的ごとにメソッドを分離（POMパターン）
    2. Browser クラスの汎用的なブラウザ操作機能を内部で使用
    3. Browserクラスのセレクタ管理機能と連携し、selectors.csvからロケーター情報を読み込み
    4. スクリーンショット、ログ記録、エラーハンドリングなどの共通機能をBrowserクラスから継承
    """
    
    # ロケーターは selectors.csv から動的に読み込まれます
    # POMパターンのロケーター定義（実際の値はCSVから動的に読み込まれる）
    account_key_input = None
    username_input = None
    password_input = None
    login_button = None
    popup_notice = None
    
    def __init__(
        self, 
        selector_group: str = 'login', 
        browser: Optional[Browser] = None,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初期化
        設定から必要な情報を読み込みます
        Browser クラスのインスタンスを使用してブラウザ操作を行います
        
        Args:
            selector_group (str): セレクタのグループ名（デフォルト: 'login'）
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
            logger (Logger): ロガーインスタンス（省略時はブラウザのロガーを使用）
            config (Dict): 設定辞書（省略時は環境変数や設定ファイルから読み込み）
        """
        # セレクタグループを設定
        self.selector_group = selector_group
        
        # ロガー設定
        self.logger = logger or self._setup_default_logger()
        
        # 設定の初期化
        self.config = config or {}
        
        # ブラウザインスタンスの初期化
        self.browser_created = False
        self._init_browser(browser)
        
        # セレクタとフォールバックロケーターの設定
        self._load_selectors_from_browser()
        
        # ログイン設定の読み込み
        self._load_config()
    
    def _setup_default_logger(self) -> logging.Logger:
        """デフォルトのロガーをセットアップする"""
        logger = logging.getLogger("login_page")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
        return logger
    
    @handle_errors(screenshot_name="browser_init_error")
    def _init_browser(self, browser=None):
        """
        ブラウザインスタンスを初期化する
        
        Args:
            browser (Browser): 既存のブラウザインスタンス
        
        Returns:
            bool: 初期化が成功した場合はTrue
        """
        self.browser_created = False
        
        if browser is None:
            # ヘッドレスモード設定を取得 - BROWSERセクションから
            headless_value = self._get_config_value("BROWSER", "headless", "false")
            headless = headless_value.lower() == "true" if isinstance(headless_value, str) else bool(headless_value)
            
            # タイムアウト設定を取得
            timeout = int(self._get_config_value("BROWSER", "timeout", "10"))
            
            # セレクタファイルのパスを設定
            selectors_path = self._get_config_value("selectors", "path", "config/selectors.csv")
            if not os.path.exists(selectors_path) and ENV_UTILS_AVAILABLE:
                selectors_path = os.path.join(str(env.get_project_root()), selectors_path)
                
            if not os.path.exists(selectors_path):
                self.logger.warning(f"セレクタファイルが見つかりません: {selectors_path}")
                selectors_path = None
            
            # ブラウザインスタンスを作成
            self.browser = Browser(
                selectors_path=selectors_path, 
                headless=headless,
                timeout=timeout,
                logger=self.logger,
                config=self.config
            )
            
            if not self.browser.setup():
                self.logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
            
            self.browser_created = True
        else:
            # 既存のブラウザインスタンスを使用
            self.browser = browser
            # ロガーが設定されてなければブラウザのロガーを使用
            if not self.logger and hasattr(browser, 'logger'):
                self.logger = browser.logger
        
        # WebDriverを取得
        self.driver = self.browser.driver
        return True
    
    def _get_config_value(self, section: str, key: str, default: Any) -> Any:
        """設定値を取得する"""
        # 設定辞書からの取得を試みる
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
            
        # env ユーティリティを使用できる場合
        if ENV_UTILS_AVAILABLE:
            return env.get_config_value(section, key, default)
            
        # 環境変数からの取得を試みる
        env_var = f"{section.upper()}_{key.upper()}"
        if env_var in os.environ:
            return os.environ[env_var]
            
        # ブラウザの設定取得メソッドがあれば使用
        if hasattr(self.browser, '_get_config_value'):
            return self.browser._get_config_value(section, key, default)
            
        return default
    
    @handle_errors(screenshot_name="load_selectors_error")
    def _load_selectors_from_browser(self):
        """
        Browser クラスのセレクタ情報から POM のロケーターを設定する
        """
        # Browser クラスのセレクタ情報が存在しない場合は終了
        if not hasattr(self.browser, 'selectors') or not self.browser.selectors:
            self.logger.warning("Browser クラスでセレクタが読み込まれていません")
            return
        
        # POMで必要なロケーターのマッピング定義
        locator_map = {
            ('login', 'account_key'): 'account_key_input',
            ('login', 'username'): 'username_input',
            ('login', 'password'): 'password_input',
            ('login', 'login_button'): 'login_button',
            ('popup', 'login_notice'): 'popup_notice'
        }
        
        # 各ロケーターをマッピングに基づいて設定
        for (group, name), attr_name in locator_map.items():
            if group in self.browser.selectors and name in self.browser.selectors[group]:
                selector_info = self.browser.selectors[group][name]
                by_type = self.browser._get_by_type(selector_info['selector_type'])
                
                if by_type:
                    # クラス変数に設定
                    setattr(LoginPage, attr_name, (by_type, selector_info['selector_value']))
                    self.logger.debug(f"ロケーター '{attr_name}' を設定しました: {by_type}={selector_info['selector_value']}")
        
        # 必要なロケーターが設定されているか確認
        missing_locators = [attr for attr in ['username_input', 'password_input', 'login_button'] 
                           if getattr(LoginPage, attr) is None]
        if missing_locators:
            self.logger.warning(f"以下のロケーターが設定されていません: {', '.join(missing_locators)}")
            self.logger.warning("selectors.csvに必要なセレクタを追加してください")
            
        self.logger.info("Browser クラスからセレクタ情報を読み込みました")
    
    def _setup_fallback_locators(self):
        """
        セレクタが見つからない場合のフォールバックロケーターを設定
        """
        # ユーザー名入力欄
        if LoginPage.username_input is None:
            LoginPage.username_input = (By.XPATH, '//input[@name="username" or @id="username" or contains(@class, "username")]')
            
        # パスワード入力欄
        if LoginPage.password_input is None:
            LoginPage.password_input = (By.XPATH, '//input[@name="password" or @id="password" or @type="password"]')
            
        # ログインボタン
        if LoginPage.login_button is None:
            LoginPage.login_button = (By.XPATH, '//button[@type="submit" or contains(@class, "submit") or contains(@class, "login")]')
            
        self.logger.debug("フォールバックロケーターを設定しました")
    
    @handle_errors(screenshot_name="load_config_error")
    def _load_config(self):
        """
        設定からログイン設定を読み込む
        config/settings.iniや環境変数から設定を読み込みます
        """
        # URL設定の読み込み
        self._load_url_config()
        
        # タイムアウト設定の読み込み
        self._load_timeout_config()
        
        # 認証設定の読み込み
        self._load_auth_config()
        
        # フォームフィールド設定の読み込み
        self._load_form_fields()
        
        # 成功/エラー判定要素の設定
        self._load_validation_elements()
        
        # 設定の検証
        self._validate_config()
        
        self.logger.info("設定ファイルからログイン設定を読み込みました")
    
    def _load_url_config(self):
        """URLに関する設定を読み込む"""
        # 基本URL設定
        self.login_url = self._get_config_value("LOGIN", "url", "")
        if not self.login_url:
            self.logger.warning("ログインURLが設定されていません")
            self.login_url = ""
        else:
            self.logger.info(f"ログインURL: {self.login_url}")
        
        # 成功判定用URL
        self.success_url = self._get_config_value("LOGIN", "success_url", "")
    
    def _load_timeout_config(self):
        """タイムアウト関連設定を読み込む"""
        # 最大試行回数
        max_attempts_value = self._get_config_value("LOGIN", "max_attempts", "3")
        self.max_attempts = int(max_attempts_value) if isinstance(max_attempts_value, str) else int(max_attempts_value or 3)
        
        # リダイレクトタイムアウト
        redirect_timeout_value = self._get_config_value("LOGIN", "redirect_timeout", "30")
        self.redirect_timeout = int(redirect_timeout_value) if isinstance(redirect_timeout_value, str) else int(redirect_timeout_value or 30)
        
        # 要素待機タイムアウト
        element_timeout_value = self._get_config_value("LOGIN", "element_timeout", "10")
        self.element_timeout = int(element_timeout_value) if isinstance(element_timeout_value, str) else int(element_timeout_value or 10)
    
    def _load_auth_config(self):
        """認証関連設定を読み込む"""
        # ベーシック認証設定
        basic_auth_value = self._get_config_value("LOGIN", "basic_auth_enabled", "false")
        self.basic_auth_enabled = basic_auth_value.lower() == "true" if isinstance(basic_auth_value, str) else bool(basic_auth_value)
        
        if self.basic_auth_enabled:
            # 環境変数から認証情報を取得（secrets.envに保存）
            self.basic_auth_username = os.environ.get("LOGIN_BASIC_AUTH_USERNAME", "")
            if not self.basic_auth_username:
                self.basic_auth_username = self._get_config_value("LOGIN", "basic_auth_username", "")
                
            self.basic_auth_password = os.environ.get("LOGIN_BASIC_AUTH_PASSWORD", "")
            if not self.basic_auth_password:
                self.basic_auth_password = self._get_config_value("LOGIN", "basic_auth_password", "")
            
            if not self.basic_auth_username or not self.basic_auth_password:
                self.logger.warning("ベーシック認証が有効ですが、ユーザー名またはパスワードが設定されていません")
                self.basic_auth_enabled = False
            else:
                self.logger.info("ベーシック認証が有効です")
                # URLにベーシック認証情報を埋め込む
                self.login_url_with_auth = self._embed_basic_auth_to_url(
                    self.login_url, self.basic_auth_username, self.basic_auth_password
                )
    
    def _load_form_fields(self):
        """フォームフィールド設定を読み込む"""
        # フォームフィールド初期化
        self.form_fields = []
        
        # アカウント番号の取得（複数アカウント対応）
        account_number = self._get_config_value("LOGIN", "account_number", "1")
        
        # ユーザー名フィールド - 環境変数（secrets.env）から取得
        username = os.environ.get(f"LOGIN_USERNAME{account_number}", "")
        if not username:
            username = os.environ.get("LOGIN_USERNAME", "")
        
        # 環境変数から取得できなかった場合は設定から取得
        if not username:
            username_config_key = f"username{account_number}"
            username = self._get_config_value("LOGIN", username_config_key, "")
            if not username:
                username = self._get_config_value("LOGIN", "username", "")
            
        if username:
            self.form_fields.append({'name': 'username', 'value': username})
            
        # パスワードフィールド - 環境変数（secrets.env）から取得
        password = os.environ.get(f"LOGIN_PASSWORD{account_number}", "")
        if not password:
            password = os.environ.get("LOGIN_PASSWORD", "")
        
        # 環境変数から取得できなかった場合は設定から取得
        if not password:
            password_config_key = f"password{account_number}"
            password = self._get_config_value("LOGIN", password_config_key, "")
            if not password:
                password = self._get_config_value("LOGIN", "password", "")
            
        if password:
            self.form_fields.append({'name': 'password', 'value': password})
        
        # アカウントキー（環境変数から取得）
        third_field_name = self._get_config_value("LOGIN", "third_field_name", "account_key")
        third_field_value = os.environ.get(f"LOGIN_{third_field_name.upper()}{account_number}", "")
        if not third_field_value:
            third_field_value = os.environ.get(f"LOGIN_{third_field_name.upper()}", "")
        
        # 環境変数から取得できなかった場合は設定から取得
        if not third_field_value:
            third_field_config_key = f"{third_field_name}{account_number}"
            third_field_value = self._get_config_value("LOGIN", third_field_config_key, "")
            if not third_field_value:
                third_field_value = self._get_config_value("LOGIN", third_field_name, "")
            
        if third_field_value:
            self.form_fields.append({'name': third_field_name, 'value': third_field_value})
            
        # ログフィールド情報（パスワードを除く）
        debug_fields = [f"{field['name']}: {field['value'] if field['name'] != 'password' else '****'}" for field in self.form_fields]
        if debug_fields:
            self.logger.debug(f"ログインフォームフィールド: {', '.join(debug_fields)}")
        else:
            self.logger.warning("ログインフォームフィールドが設定されていません")
    
    def _load_validation_elements(self):
        """ログイン成功/失敗判定用の要素設定を読み込む"""
        # 成功要素
        success_element_selector = self._get_config_value("LOGIN", "success_element_selector", "")
        success_element_type_str = self._get_config_value("LOGIN", "success_element_type", "css")
        
        self.success_element = {
            'type': success_element_type_str,
            'selector': success_element_selector
        } if success_element_selector else None
        
        # エラー要素
        error_selector = self._get_config_value("LOGIN", "error_selector", "")
        error_type_str = self._get_config_value("LOGIN", "error_type", "css")
        
        self.error_selector = {
            'type': error_type_str,
            'selector': error_selector
        } if error_selector else None
    
    def _validate_config(self):
        """設定の妥当性を検証する"""
        if not self.login_url:
            self.logger.warning("ログインURLが設定されていません。navigate_to_login_page()メソッドの実行時にURLを指定する必要があります。")
        
        if not self.form_fields:
            self.logger.warning("ログインフォームのフィールドが設定されていません")
    
    def _embed_basic_auth_to_url(self, url, username, password):
        """
        URLにベーシック認証情報を埋め込む
        
        Args:
            url (str): 元のURL
            username (str): ベーシック認証のユーザー名
            password (str): ベーシック認証のパスワード
            
        Returns:
            str: ベーシック認証情報が埋め込まれたURL
        """
        try:
            # URLをパース
            parsed_url = urllib.parse.urlparse(url)
            
            # ベーシック認証情報を追加
            netloc = f"{username}:{password}@{parsed_url.netloc}"
            
            # URLを再構築
            auth_url = parsed_url._replace(netloc=netloc).geturl()
            
            self.logger.debug(f"ベーシック認証情報を埋め込んだURL: {auth_url}")
            return auth_url
            
        except Exception as e:
            self.logger.error(f"URLへのベーシック認証情報埋め込み中にエラーが発生しました: {str(e)}")
            return url 

    @handle_errors(screenshot_name="login_error", raise_exception=True)
    def navigate_to_login_page(self, url=None):
        """
        ログインページに移動する
        
        Args:
            url (str, optional): ログインページのURL（省略時は設定から読み込み）
            
        Returns:
            bool: 成功時はTrue
        """
        # URLの設定
        target_url = url or self.login_url
        if not target_url:
            self.logger.error("ログインURLが指定されていません")
            raise ValueError("ログインURLが指定されていません")
            
        self.logger.info(f"ログインページに移動します: {target_url}")
        
        # ベーシック認証が有効な場合
        if self.basic_auth_enabled and hasattr(self, 'login_url_with_auth'):
            # ベーシック認証情報が埋め込まれたURLに移動
            result = self.browser.navigate_to(self.login_url_with_auth)
        else:
            # 通常のURLに移動
            result = self.browser.navigate_to(target_url)
        
        if not result:
            self.logger.error("ログインページへの移動に失敗しました")
            raise LoginError("ログインページへの移動に失敗しました")
            
        # ページのロードを待機
        self.logger.info("ログインページが読み込まれました")
        
        # 設定からページロード待機時間を取得
        page_load_wait = int(self._get_config_value("LOGIN", "page_load_wait", "1"))
        time.sleep(page_load_wait)  # 一時停止してページの読み込みを待機
        
        # 必要に応じてページのロード完了を待機（JavaScriptのロードなど）
        self.wait_for_page_load()
        
        # スクリーンショットを取得（オプション）
        screenshot_on_login = self._get_config_value("LOGIN", "screenshot_on_login", "true").lower() == "true"
        if screenshot_on_login:
            self.browser.save_screenshot("login_page.png")
        
        return True
    
    @handle_errors(screenshot_name="wait_page_load_error")
    def wait_for_page_load(self, timeout=None):
        """
        ページのロード完了を待機する
        
        Args:
            timeout (int, optional): タイムアウト秒数（省略時は設定から読み込み）
            
        Returns:
            bool: 成功時はTrue
        """
        # タイムアウト設定
        wait_timeout = timeout or self.element_timeout
        
        try:
            # ページのロード完了を待機
            WebDriverWait(self.driver, wait_timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            self.logger.debug("ページのロード完了を確認しました")
            return True
        except TimeoutException:
            self.logger.warning(f"{wait_timeout}秒経過してもページのロードが完了しませんでした")
            return False
    
    @handle_errors(screenshot_name="waiting_element_error")
    def wait_for_element(self, locator, timeout=None, visible=True):
        """
        要素が表示されるまで待機する
        
        Args:
            locator (tuple): 要素のロケータータプル (By.XXX, 'selector')
            timeout (int, optional): タイムアウト秒数
            visible (bool): Trueの場合は可視性も確認、Falseの場合は存在のみ確認
            
        Returns:
            WebElement or None: 要素が見つかった場合はその要素、見つからない場合はNone
        """
        # タイムアウト設定
        wait_timeout = timeout or self.element_timeout
        
        try:
            wait = WebDriverWait(self.driver, wait_timeout)
            
            if visible:
                # 要素が可視状態になるまで待機
                element = wait.until(EC.visibility_of_element_located(locator))
            else:
                # 要素が存在するまで待機
                element = wait.until(EC.presence_of_element_located(locator))
                
            self.logger.debug(f"要素を確認しました: {locator}")
            return element
        except TimeoutException:
            self.logger.warning(f"{wait_timeout}秒経過しても要素が見つかりませんでした: {locator}")
            return None
        except Exception as e:
            self.logger.error(f"要素待機中にエラーが発生しました: {str(e)}")
            return None
    
    @handle_errors(screenshot_name="detect_auth_error")
    def detect_and_handle_auth_redirect(self):
        """
        認証画面へのリダイレクトを検出して処理する
        
        Returns:
            bool: 処理が成功した場合はTrue
        """
        # 認証画面の特徴的な要素を検出
        if hasattr(LoginPage, 'account_key_input') and LoginPage.account_key_input:
            # アカウントキー入力欄があるか確認
            account_key_element = self.wait_for_element(LoginPage.account_key_input, timeout=5, visible=True)
            
            if account_key_element:
                self.logger.info("アカウントキー認証画面を検出しました")
                
                # アカウントキーフィールドがあるか確認
                account_key_field = next((field for field in self.form_fields if field['name'] == 'account_key'), None)
                
                if account_key_field:
                    # アカウントキーを入力して送信
                    account_key_element.clear()
                    account_key_element.send_keys(account_key_field['value'])
                    
                    # 送信ボタンを探して押下
                    submit_button = self.wait_for_element(LoginPage.login_button, timeout=5)
                    if submit_button:
                        submit_button.click()
                        self.logger.info("アカウントキーを送信しました")
                        time.sleep(2)  # 処理を待機
                        return True
                else:
                    self.logger.warning("アカウントキーが設定されていません")
                    
        return False
    
    @handle_errors(screenshot_name="fill_form_error")
    def fill_login_form(self):
        """
        ログインフォームに情報を入力する
        
        Returns:
            bool: 成功時はTrue
        """
        # フォールバックロケーターの設定
        self._setup_fallback_locators()
        
        # ログイン前に認証画面を処理
        self.detect_and_handle_auth_redirect()
        
        # ユーザー名入力
        username_field = next((field for field in self.form_fields if field['name'] == 'username'), None)
        if username_field and LoginPage.username_input:
            username_element = self.wait_for_element(LoginPage.username_input)
            if username_element:
                self.logger.info("ユーザー名入力欄を確認しました")
                username_element.clear()
                username_element.send_keys(username_field['value'])
            else:
                self.logger.error("ユーザー名入力欄が見つかりません")
                raise LoginError("ユーザー名入力欄が見つかりません")
        
        # パスワード入力
        password_field = next((field for field in self.form_fields if field['name'] == 'password'), None)
        if password_field and LoginPage.password_input:
            password_element = self.wait_for_element(LoginPage.password_input)
            if password_element:
                self.logger.info("パスワード入力欄を確認しました")
                password_element.clear()
                password_element.send_keys(password_field['value'])
            else:
                self.logger.error("パスワード入力欄が見つかりません")
                raise LoginError("パスワード入力欄が見つかりません")
        
        # デバッグ用にスクリーンショットを保存
        self.browser.save_screenshot("login_form_filled.png")
        
        return True
    
    @handle_errors(screenshot_name="login_submit_error")
    def submit_login_form(self):
        """
        ログインフォームを送信する
        
        Returns:
            bool: 送信が成功した場合はTrue
        """
        self.logger.info("ログインフォームを送信します")
        
        # フォームフィールドの存在確認
        if not self.form_fields:
            self.logger.error("フォームフィールドが設定されていません")
            return False
        
        # フォーム入力前の状態を記録
        before_submit_url = self.driver.current_url
        
        # フォームに入力
        for field in self.form_fields:
            # フィールド情報を取得
            field_name = field['name']
            field_value = field['value']
            
            # セレクタの決定
            if field_name == 'username' and LoginPage.username_input:
                field_locator = LoginPage.username_input
            elif field_name == 'password' and LoginPage.password_input:
                field_locator = LoginPage.password_input
            elif field_name == 'account_key' and LoginPage.account_key_input:
                field_locator = LoginPage.account_key_input
            else:
                self.logger.warning(f"フィールド '{field_name}' のセレクタが定義されていません")
                continue
            
            # 要素を探して入力
            try:
                # ブラウザの新しい wait_for_element メソッドを使用
                element = self.browser.wait_for_element(field_locator, timeout=self.element_timeout, visible=True)
                
                if not element:
                    self.logger.error(f"入力フィールド '{field_name}' が見つかりません")
                    continue
                
                # フィールドへのスクロール
                self.browser.scroll_to_element(element)
                
                # フィールドを一度クリア
                element.clear()
                
                # 値を入力
                element.send_keys(field_value)
                
                # マスク処理してログに記録
                masked_value = "****" if field_name == "password" else field_value
                self.logger.info(f"フィールド '{field_name}' に値を入力しました: {masked_value}")
                
            except Exception as e:
                self.logger.error(f"フィールド '{field_name}' への入力中にエラーが発生しました: {str(e)}")
                continue
        
        # ログインボタンのクリック
        if LoginPage.login_button:
            try:
                # ブラウザの click_element メソッドを使用
                login_success = self.browser.click_element_by_xpath(LoginPage.login_button[1]) if LoginPage.login_button[0] == By.XPATH else False
                
                if not login_success:
                    # デフォルトのクリック方法に戻る
                    submit_button = self.browser.wait_for_element(LoginPage.login_button, timeout=self.element_timeout)
                    if submit_button:
                        self.browser.scroll_to_element(submit_button)
                        submit_button.click()
                        self.logger.info("ログインボタンをクリックしました")
                    else:
                        self.logger.error("ログインボタンが見つかりません")
                        return False
            except Exception as e:
                self.logger.error(f"ログインボタンのクリック中にエラーが発生しました: {str(e)}")
                return False
                
            # ページ変更を検出
            try:
                # ブラウザの新機能を使用してページ変更を検出
                if self.browser.detect_page_changes(wait_seconds=3):
                    self.logger.info("ページの変更を検出しました")
                else:
                    self.logger.warning("ログイン後のページ変更が検出されませんでした")
            except:
                pass
                
            # 成功認証ページへのリダイレクトを待機
            wait_redirect = True  # デフォルトで待機
            
            # 設定からリダイレクト待機の有無を確認
            redirect_wait_setting = self._get_config_value("LOGIN", "wait_for_redirect", "true")
            if isinstance(redirect_wait_setting, str):
                wait_redirect = redirect_wait_setting.lower() == "true"
            else:
                wait_redirect = bool(redirect_wait_setting)
                
            if wait_redirect:
                redirect_success = self._wait_for_redirect(before_submit_url)
                return redirect_success
            
            return True
        else:
            self.logger.error("ログインボタンのセレクタが定義されていません")
            return False
    
    @handle_errors(screenshot_name="wait_redirect_error")
    def wait_for_login_redirect(self):
        """
        ログイン後のリダイレクトを待機する
        
        Returns:
            bool: リダイレクトが確認された場合はTrue
        """
        # 初期URL取得
        start_url = self.driver.current_url
        
        # ログイン成功判定用URL
        if self.success_url:
            try:
                # 最大待機時間
                end_time = time.time() + self.redirect_timeout
                
                while time.time() < end_time:
                    # 現在のURLが成功URLを含むかチェック
                    current_url = self.driver.current_url
                    
                    if self.success_url in current_url:
                        self.logger.info(f"リダイレクト先に成功URLが含まれています: {current_url}")
                        return True
                    
                    # 初期URLから変わったかチェック
                    if current_url != start_url:
                        self.logger.info(f"リダイレクトを検出しました: {start_url} -> {current_url}")
                        return True
                    
                    # 待機
                    time.sleep(1)
                
                self.logger.warning(f"{self.redirect_timeout}秒経過してもリダイレクトが完了しませんでした")
                return False
                
            except Exception as e:
                self.logger.error(f"リダイレクト待機中にエラーが発生しました: {str(e)}")
                return False
        else:
            # 成功URLが設定されていない場合は3秒待って成功を返す
            time.sleep(3)
            return True
    
    @handle_errors(screenshot_name="check_login_result_error")
    def check_login_result(self):
        """
        ログイン結果を確認する
        
        Returns:
            bool: ログイン成功時はTrue、失敗時はFalse
        """
        # 成功要素が設定されている場合
        if self.success_element:
            try:
                # 要素の存在を確認
                by_type = self.browser._get_by_type(self.success_element['type'])
                if by_type:
                    success_locator = (by_type, self.success_element['selector'])
                    element = self.wait_for_element(success_locator, timeout=5)
                    
                    if element:
                        self.logger.info("ログイン成功を確認しました")
                        return True
                    else:
                        self.logger.warning("ログイン成功要素が見つかりません")
            except Exception as e:
                self.logger.error(f"ログイン成功確認中にエラーが発生しました: {str(e)}")
        
        # エラー要素が設定されている場合
        if self.error_selector:
            try:
                # エラー要素の存在を確認
                by_type = self.browser._get_by_type(self.error_selector['type'])
                if by_type:
                    error_locator = (by_type, self.error_selector['selector'])
                    element = self.wait_for_element(error_locator, timeout=3)
                    
                    if element:
                        error_text = element.text
                        self.logger.error(f"ログインエラーが発生しました: {error_text}")
                        return False
            except Exception as e:
                self.logger.error(f"ログインエラー確認中にエラーが発生しました: {str(e)}")
        
        # 通知ポップアップが設定されている場合
        if LoginPage.popup_notice:
            try:
                # 通知ポップアップの存在を確認
                element = self.wait_for_element(LoginPage.popup_notice, timeout=3)
                if element:
                    popup_text = element.text
                    self.logger.info(f"ログイン後の通知を確認しました: {popup_text}")
            except Exception as e:
                self.logger.error(f"通知ポップアップ確認中にエラーが発生しました: {str(e)}")
        
        # 成功とエラーの両方が確認できない場合は、現在のURLをチェック
        if self.success_url:
            return self.success_url in self.driver.current_url
        
        # すべての確認が取れなかった場合はTrueを返す
        self.logger.info("ログイン処理を完了しました（明示的な成功/失敗の確認はできませんでした）")
        return True
    
    @handle_errors(screenshot_name="login_process_error", raise_exception=True)
    def login(self, url=None, max_attempts=None):
        """
        ログイン処理の一連の流れを実行する
        
        Args:
            url (str, optional): ログインページのURL（省略時は設定から読み込み）
            max_attempts (int, optional): 最大試行回数（省略時は設定から読み込み）
            
        Returns:
            bool: ログイン成功時はTrue
        """
        # 最大試行回数の設定
        attempts = max_attempts or self.max_attempts
        
        for attempt in range(1, attempts + 1):
            try:
                self.logger.info(f"ログイン処理を開始します（試行 {attempt}/{attempts}）")
                
                # ログインページに移動
                self.navigate_to_login_page(url)
                
                # ログインフォームに情報を入力
                self.fill_login_form()
                
                # ログインフォームを送信
                self.submit_login_form()
                
                # ログイン結果の確認
                result = self.check_login_result()
                
                if result:
                    self.logger.info("ログインに成功しました")
                    return True
                else:
                    self.logger.warning(f"ログインに失敗しました（試行 {attempt}/{attempts}）")
                    
                    # 最終試行の場合はエラーで終了
                    if attempt == attempts:
                        self.logger.error("最大試行回数に達しました")
                        raise LoginError("最大試行回数に達しました")
                        
                    # 次の試行のための待機
                    time.sleep(3)
            except Exception as e:
                self.logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
                
                # 最終試行の場合はエラーで終了
                if attempt == attempts:
                    self.logger.error("最大試行回数に達しました")
                    raise LoginError(f"ログイン処理に失敗しました: {str(e)}")
                
                # 次の試行のための待機
                time.sleep(3)
        
        return False
    
    def close(self):
        """
        ブラウザを閉じる（このクラスで作成した場合のみ）
        """
        if self.browser_created and hasattr(self, 'browser'):
            self.logger.info("ブラウザを閉じます")
            self.browser.close()
    
    def __enter__(self):
        """コンテキストマネージャー対応（with文でのリソース管理）"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了時処理"""
        self.close()
        return False  # 例外を伝播させる


def main():
    """
    テスト用のメイン関数
    """
    import argparse
    
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description="汎用ログインページテスト")
    parser.add_argument('--url', help='ログインページのURL', default='')
    parser.add_argument('--headless', help='ヘッドレスモードで実行する', action='store_true')
    parser.add_argument('--username', help='ユーザー名', default='')
    parser.add_argument('--password', help='パスワード', default='')
    
    args = parser.parse_args()
    
    # ロガーの設定
    logger = logging.getLogger("login_test")
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # 設定の作成
    config = {
        'browser': {
            'headless': 'true' if args.headless else 'false'
        },
        'login': {
            'url': args.url,
            'username': args.username,
            'password': args.password,
        }
    }
    
    try:
        # ログインページの作成
        with LoginPage(logger=logger, config=config) as login_page:
            # ログイン処理の実行
            result = login_page.login()
            
            if result:
                logger.info("ログインテストが成功しました")
                return 0
            else:
                logger.error("ログインテストが失敗しました")
                return 1
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main()) 