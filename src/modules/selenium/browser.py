#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汎用的なブラウザ操作モジュール

Seleniumの機能をラップし、設定ファイルを活用した
スクリーンショットやセレクタの管理を提供します。
"""

import os
import sys
import time
import logging
import csv
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Tuple, Callable
import urllib.parse
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

# BeautifulSoupのインポート（可能であれば）
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# 環境変数操作用のユーティリティをインポート（存在する場合）
try:
    from src.utils.environment import env
    ENV_UTILS_AVAILABLE = True
except ImportError:
    ENV_UTILS_AVAILABLE = False


class Browser:
    """
    WebブラウザとWebページの操作を提供するラッパークラス
    
    このクラスはSeleniumの機能をラップし、以下の機能を提供します:
    - 設定ファイルからのブラウザ設定の読み込み
    - セレクタの外部ファイル (CSV) からの読み込み
    - スクリーンショットの取得と管理
    - エラー通知（オプション）
    - ページの解析と要素の操作
    """
    
    def __init__(
        self, 
        logger: Optional[logging.Logger] = None,
        selectors_path: Optional[str] = None, 
        headless: Optional[bool] = None,
        timeout: int = 10,
        config: Optional[Dict[str, Any]] = None,
        notifier: Optional[Any] = None,
        project_root: Optional[str] = None
    ):
        """
        ブラウザインスタンスの初期化
        
        Args:
            logger: カスタムロガー（指定されていない場合は新規作成）
            selectors_path: セレクタを含むCSVファイルのパス
            headless: ヘッドレスモードを有効にするかどうか
            timeout: デフォルトのタイムアウト（秒）
            config: 設定辞書（指定された場合はこれを優先使用）
            notifier: 通知を送信するためのオブジェクト（省略可能）
            project_root: プロジェクトのルートディレクトリ
        """
        # ロガーの設定
        self.logger = logger or self._setup_default_logger()
        
        # プロジェクトルートの設定
        self.project_root = project_root or self._get_project_root()
        
        # 設定の初期化
        self.config = config or {}
        
        # セレクタのパス設定
        self.selectors_path = selectors_path
        if self.selectors_path and not os.path.isabs(self.selectors_path):
            self.selectors_path = self._resolve_path(self.selectors_path)
        
        # ブラウザ設定
        self.timeout = timeout
        
        # settings.ini から headless モードを読み込む（引数で指定されていない場合）
        if headless is None:
            headless_str = self._get_config_value("BROWSER", "headless", "false")
            self.headless = headless_str.lower() == "true"
        else:
            self.headless = headless
        
        # スクリーンショット設定を読み込む
        self._load_screenshot_settings()
            
        # 通知機能
        self.notifier = notifier
        
        # ドライバーと状態の初期化
        self.driver = None
        self.selectors = {}
        self.current_page_source = None
        self.last_page_source = None
        
        # ログ出力
        self.logger.debug(f"Browserクラスを初期化しました (headless: {self.headless})")
    
    def _setup_default_logger(self) -> logging.Logger:
        """
        デフォルトのロガーをセットアップする
        
        Returns:
            logging.Logger: 設定されたロガーインスタンス
        """
        logger = logging.getLogger("browser")
        
        # ハンドラが未設定なら追加
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
        return logger
    
    def _get_project_root(self) -> str:
        """
        プロジェクトのルートディレクトリを特定する
        
        Returns:
            str: プロジェクトルートのパス
        """
        # env ユーティリティを使用できる場合はそちらを優先
        if ENV_UTILS_AVAILABLE:
            return str(env.get_project_root())
        
        # 現在のファイルの絶対パス
        current_file = os.path.abspath(__file__)
        
        # src または modules ディレクトリを探す
        parts = current_file.split(os.sep)
        for i in range(len(parts) - 1, 0, -1):
            if parts[i] in ['src', 'modules', 'selenium']:
                # 見つかったディレクトリの親をプロジェクトルートとする
                return os.sep.join(parts[:i])
        
        # 見つからなければカレントディレクトリを返す
        return os.getcwd()
    
    def _resolve_path(self, path: str) -> str:
        """
        相対パスを絶対パスに解決する
        
        Args:
            path: 解決する相対パス
            
        Returns:
            str: 解決された絶対パス
        """
        if os.path.isabs(path):
            return path
        return os.path.join(self.project_root, path)
    
    def _get_config_value(self, section: str, key: str, default: Any) -> Any:
        """
        設定値を取得する
        優先度: 1. self.config 2. env.get_config_value 3. デフォルト値
        
        Args:
            section: 設定セクション
            key: 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
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
        
        return default
    
    def _load_screenshot_settings(self):
        """スクリーンショット関連の設定を読み込む"""
        try:
            # スクリーンショット基本設定
            auto_screenshot_config = self._get_config_value("BROWSER", "auto_screenshot", "true")
            
            # 型チェックと変換処理を強化
            if isinstance(auto_screenshot_config, bool):
                self.auto_screenshot = auto_screenshot_config
            elif isinstance(auto_screenshot_config, str):
                self.auto_screenshot = auto_screenshot_config.lower() in ("true", "yes", "1", "on")
            else:
                self.auto_screenshot = True  # デフォルト値
                self.logger.warning(f"不正なauto_screenshot設定値: {auto_screenshot_config}")
            
            self.screenshot_dir = self._get_config_value("BROWSER", "screenshot_dir", "logs/screenshots")
            self.screenshot_format = self._get_config_value("BROWSER", "screenshot_format", "png")
            
            # スクリーンショット品質の設定
            screenshot_quality_config = self._get_config_value("BROWSER", "screenshot_quality", "100")
            if isinstance(screenshot_quality_config, int):
                self.screenshot_quality = screenshot_quality_config
            else:
                try:
                    self.screenshot_quality = int(screenshot_quality_config)
                except (ValueError, TypeError):
                    self.screenshot_quality = 100  # デフォルト値
                    self.logger.warning(f"不正なscreenshot_quality設定値: {screenshot_quality_config}")
            
            # エラー時のスクリーンショット設定
            screenshot_on_error_config = self._get_config_value("BROWSER", "screenshot_on_error", "true")
            if isinstance(screenshot_on_error_config, bool):
                self.screenshot_on_error = screenshot_on_error_config
            elif isinstance(screenshot_on_error_config, str):
                self.screenshot_on_error = screenshot_on_error_config.lower() in ("true", "yes", "1", "on")
            else:
                self.screenshot_on_error = True  # デフォルト値
                self.logger.warning(f"不正なscreenshot_on_error設定値: {screenshot_on_error_config}")
            
            # パスが相対パスの場合、絶対パスに変換
            if not os.path.isabs(self.screenshot_dir):
                self.screenshot_dir = os.path.join(self.project_root, self.screenshot_dir)
            
            self.logger.debug(f"スクリーンショット設定を読み込みました: auto_screenshot={self.auto_screenshot}, "
                             f"screenshot_on_error={self.screenshot_on_error}, format={self.screenshot_format}")
        
        except Exception as e:
            # エラー発生時はデフォルト値を設定
            self.logger.error(f"スクリーンショット設定の読み込み中にエラーが発生しました: {str(e)}")
            self.auto_screenshot = False  # エラー時はスクリーンショットを無効化
            self.screenshot_on_error = True
            self.screenshot_dir = os.path.join(self.project_root, "logs/screenshots")
            self.screenshot_format = "png"
            self.screenshot_quality = 80
    
    def _setup_fallback_selectors(self):
        """フォールバックセレクタを設定する"""
        # セレクタがまだ設定されていない場合に初期化
        if not self.selectors:
            self.selectors = {
                'login': {
                    'username': {'selector_type': 'id', 'selector_value': 'username', 'description': 'ユーザー名入力欄'},
                    'password': {'selector_type': 'id', 'selector_value': 'password', 'description': 'パスワード入力欄'},
                    'login_button': {'selector_type': 'css', 'selector_value': '.loginbtn', 'description': 'ログインボタン'},
                    'account_key': {'selector_type': 'id', 'selector_value': 'account_key', 'description': 'アカウントキー入力欄'}
                }
            }
            self.logger.warning("セレクタファイルが読み込めないため、デフォルトセレクタを使用します")
    
    def _load_selectors(self):
        """
        CSVファイルからセレクタを読み込む
        
        CSVフォーマット:
        group,name,selector_type,selector_value,description
        login,username,id,username,ユーザー名入力欄
        login,password,id,password,パスワード入力欄
        ...
        """
        # セレクタパスが指定されていない場合はデフォルトパスを使用
        if not self.selectors_path:
            default_path = self._get_config_value("selectors", "path", "config/selectors.csv")
            self.selectors_path = self._resolve_path(default_path)
            self.logger.debug(f"デフォルトのセレクタパスを使用: {self.selectors_path}")
        
        # ファイルが存在するか確認
        if not os.path.exists(self.selectors_path):
            self.logger.warning(f"セレクタファイルが見つかりません: {self.selectors_path}")
            self._setup_fallback_selectors()
            return
        
        try:
            # CSVファイルを読み込む
            with open(self.selectors_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # セレクタの辞書を初期化
                self.selectors = {}
                
                # 各行を処理
                for row in reader:
                    group = row['group']
                    name = row['name']
                    selector_type = row['selector_type']
                    selector_value = row['selector_value']
                    description = row.get('description', '')
                        
                    # グループが存在しなければ作成
                    if group not in self.selectors:
                        self.selectors[group] = {}
                        
                    # セレクタを追加
                    self.selectors[group][name] = {
                        'selector_type': selector_type,
                        'selector_value': selector_value,
                        'description': description
                    }
            
            self.logger.info(f"セレクタをロードしました: {len(self.selectors)} グループ")
            
            # ロードしたセレクタの詳細をデバッグ出力
            for group, selectors in self.selectors.items():
                self.logger.debug(f"グループ '{group}': {len(selectors)} セレクタ")
            
        except Exception as e:
            self.logger.error(f"セレクタの読み込み中にエラーが発生しました: {str(e)}")
            self._setup_fallback_selectors()
    
    def setup(self, browser_version=None):
        """
        ブラウザドライバーを初期化する
        
        Args:
            browser_version: 特定のブラウザバージョンに対応するドライバーをインストールする場合に指定（省略可能）
        
        Returns:
            bool: 成功した場合はTrue、それ以外はFalse
        """
        try:
            # Chromeのオプションを設定
            chrome_options = Options()
            
            # ヘッドレスモードの設定
            if self.headless:
                chrome_options.add_argument("--headless")
                self.logger.info("ヘッドレスモードを有効化しました")
            
            # その他の一般的なオプション
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # GPUエラーを回避するためのオプションを追加
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-gl-drawing-for-tests")
            
            # ブラウザのサイズを設定
            window_width = self._get_config_value("BROWSER", "window_width", "1920")
            window_height = self._get_config_value("BROWSER", "window_height", "1080")
            chrome_options.add_argument(f"--window-size={window_width},{window_height}")
            
            # 言語設定
            chrome_options.add_argument("--lang=ja")
            
            # 追加のオプション（設定ファイルから読み込み）
            additional_options = self._get_config_value("BROWSER", "additional_options", "")
            if additional_options:
                for option in additional_options.split(","):
                    option = option.strip()
                    if option:
                        chrome_options.add_argument(option)
                        self.logger.debug(f"追加のブラウザオプション: {option}")
            
            # ローカルのChromeドライバーを使用
            try:
                # 最もシンプルな方法でChromeドライバーを初期化
                self.logger.info("直接ChromeDriverを初期化します")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.logger.info("ChromeDriverの初期化に成功しました")
            except Exception as local_driver_error:
                self.logger.warning(f"直接初期化に失敗しました: {str(local_driver_error)}")
                
                try:
                    # WebDriverManagerを使用したフォールバック
                    self.logger.info("WebDriverManagerを使用して初期化を試みます")
                    
                    # 設定ファイルからブラウザバージョンを読み込む（引数で指定されていない場合）
                    if browser_version is None:
                        browser_version = self._get_config_value("BROWSER", "chrome_version", None)
                    
                    # バージョン指定がある場合は特定バージョンのドライバーをインストール
                    service = None
                    if browser_version:
                        try:
                            self.logger.info(f"Chrome バージョン {browser_version} 用のドライバーをインストールします")
                            service = Service(ChromeDriverManager(version=browser_version).install())
                        except Exception as e:
                            self.logger.warning(f"指定されたバージョン {browser_version} のドライバー取得に失敗しました: {str(e)}")
                            self.logger.info("最新のドライバーにフォールバックします")
                    
                    # バージョン指定がない場合や前のステップで失敗した場合
                    if service is None:
                        self.logger.info("現在のChromeバージョンに適合するドライバーを自動検出します")
                        service = Service(ChromeDriverManager().install())
                    
                    # WebDriverを初期化
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as wdm_error:
                    self.logger.error(f"WebDriverManagerでの初期化も失敗しました: {str(wdm_error)}")
                    raise Exception("すべてのChromeDriver初期化方法に失敗しました") from wdm_error
            
            # タイムアウトを設定
            self.driver.implicitly_wait(self.timeout)
            
            # セレクタを読み込む
            self._load_selectors()
            
            # スクリーンショットディレクトリの作成
            if self.auto_screenshot or self.screenshot_on_error:
                os.makedirs(self.screenshot_dir, exist_ok=True)
                self.logger.debug(f"スクリーンショットディレクトリを確認: {self.screenshot_dir}")
            
            self.logger.info("ブラウザの初期化に成功しました")
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザのセットアップ中にエラーが発生しました: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            if self.notifier:
                self._notify_error("ブラウザのセットアップに失敗しました", exception=e)
                
            return False 

    def navigate_to(self, url):
        """
        指定したURLに移動する
        
        Args:
            url: 移動先のURL
            
        Returns:
            bool: 成功した場合はTrue、それ以外はFalse
        """
        if not self.driver:
            self.logger.error("ドライバーが初期化されていません。setup()を先に呼び出してください。")
            return False
        
        try:
            self.logger.info(f"URLに移動します: {url}")
            self.driver.get(url)
            
            # ページ読み込みの完了を待機
            if not self.wait_for_page_load():
                self.logger.warning("ページの読み込みが完了しなかった可能性があります")
            
            # 現在のページソースを保存
            self.last_page_source = self.current_page_source
            self.current_page_source = self.driver.page_source
            
            # 自動スクリーンショットが有効な場合
            if self.auto_screenshot:
                screenshot_name = f"navigate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.save_screenshot(screenshot_name, append_url=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"URLへの移動中にエラーが発生しました: {str(e)}")
            
            if self.screenshot_on_error:
                self.save_screenshot(f"error_navigate_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                
            if self.notifier:
                self._notify_error("ページへの移動に失敗しました", exception=e, context={"url": url})
                
            return False
    
    def _get_by_type(self, selector_type):
        """
        セレクタタイプに対応するByタイプを返す
        
        Args:
            selector_type: セレクタタイプ（id, css, xpath, name, tag, link_text, partial_link_text）
            
        Returns:
            By: Seleniumの By クラス、または対応するものがない場合はNone
        """
        selector_type = selector_type.lower()
        
        if selector_type == 'id':
            return By.ID
        elif selector_type == 'css':
            return By.CSS_SELECTOR
        elif selector_type == 'xpath':
            return By.XPATH
        elif selector_type == 'name':
            return By.NAME
        elif selector_type == 'tag':
            return By.TAG_NAME
        elif selector_type == 'link_text':
            return By.LINK_TEXT
        elif selector_type == 'partial_link_text':
            return By.PARTIAL_LINK_TEXT
        elif selector_type == 'class':
            return By.CLASS_NAME
        else:
            self.logger.warning(f"未知のセレクタタイプです: {selector_type}")
            return None

    def get_element(self, group, name, wait_time=None, visible=False):
        """
        セレクタグループと名前を使用して要素を取得する
        
        Args:
            group: セレクタグループ
            name: セレクタ名
            wait_time: 待機時間（秒、Noneの場合はデフォルト値を使用）
            visible: 要素が表示されていることを確認するかどうか
            
        Returns:
            WebElement or None: 要素が見つかった場合はその要素、見つからない場合はNone
        """
        if not self.driver:
            self.logger.error("ドライバーが初期化されていません")
            return None
        
        # セレクタが読み込まれていない場合はロード
        if not self.selectors:
            self._load_selectors()
            
        # セレクタが存在するか確認
        if group not in self.selectors or name not in self.selectors[group]:
            self.logger.error(f"セレクタが見つかりません: グループ={group}, 名前={name}")
            return None
        
        # wait_for_element を利用して要素を取得
        return self.wait_for_element((group, name), timeout=wait_time, visible=visible)
    
    def save_screenshot(self, filename, append_timestamp=False, append_url=False, custom_dir=None):
        """
        スクリーンショットを保存する
        
        Args:
            filename: スクリーンショットのファイル名（拡張子なし）
            append_timestamp: ファイル名にタイムスタンプを追加するかどうか
            append_url: ファイル名にURLの一部を追加するかどうか
            custom_dir: カスタムディレクトリ（Noneの場合はデフォルトを使用）
            
        Returns:
            str or None: 保存されたファイルのパス、または失敗した場合はNone
        """
        if not self.driver:
            self.logger.error("ドライバーが初期化されていません")
            return None
        
        try:
            # 保存先ディレクトリの設定
            save_dir = custom_dir if custom_dir else self.screenshot_dir
            
            # ディレクトリが存在しない場合は作成
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # ファイル名の作成
            base_filename = filename
            
            # タイムスタンプの追加
            if append_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"{base_filename}_{timestamp}"
                
            # URLの追加（オプション）
            if append_url and self.driver.current_url:
                try:
                    parsed_url = urllib.parse.urlparse(self.driver.current_url)
                    domain = parsed_url.netloc.replace(".", "_")
                    path = parsed_url.path.replace("/", "_")
                    if len(path) > 30:  # URLが長すぎる場合は切り詰める
                        path = path[:30]
                    url_part = f"{domain}{path}"
                    base_filename = f"{base_filename}_{url_part}"
                except:
                    # URL解析に失敗した場合は無視
                    pass
            
            # ファイル名をサニタイズ（ファイル名に使えない文字を除去）
            base_filename = "".join(c for c in base_filename if c.isalnum() or c in "_-.")
            
            # フォーマットを適用
            format_ext = self.screenshot_format.lower()
            if not format_ext.startswith('.'):
                format_ext = f".{format_ext}"
                
            # 完全なファイルパスを作成
            filepath = os.path.join(save_dir, f"{base_filename}{format_ext}")
            
            # スクリーンショットを保存
            self.driver.save_screenshot(filepath)
            
            self.logger.info(f"スクリーンショットを保存しました: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"スクリーンショットの保存中にエラーが発生しました: {str(e)}")
            return None
    
    def _notify_error(self, error_message, exception=None, context=None):
        """
        エラーを通知する
        
        Args:
            error_message: エラーメッセージ
            exception: 例外オブジェクト（省略可能）
            context: コンテキスト情報（省略可能）
        """
        if not self.notifier:
            return
            
        try:
            # 現在のURLを取得
            current_url = self.driver.current_url if self.driver else "不明"
            
            # スクリーンショットを撮影
            screenshot_path = None
            if self.driver and self.screenshot_on_error:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = self.save_screenshot(f"error_notification_{timestamp}")
                
            # 例外の詳細を取得
            exception_details = str(exception) if exception else "不明"
            traceback_info = traceback.format_exc() if exception else ""
            
            # 通知データの作成
            notification_data = {
                "error_message": error_message,
                "exception": exception_details,
                "traceback": traceback_info,
                "url": current_url,
                "timestamp": datetime.now().isoformat(),
                "screenshot_path": screenshot_path
            }
            
            # コンテキスト情報を追加
            if context:
                notification_data["context"] = context
                
            # 通知を送信
            self.notifier.send_error_notification(notification_data)
            self.logger.info("エラー通知を送信しました")
            
        except Exception as e:
            self.logger.error(f"エラー通知の送信中にエラーが発生しました: {str(e)}")
    
    def quit(self, error_message=None, exception=None, context=None):
        """
        ブラウザを終了する
        
        Args:
            error_message: エラーメッセージ（省略可能）
            exception: 例外オブジェクト（省略可能）
            context: コンテキスト情報（省略可能）
        """
        try:
            # エラーメッセージが提供されている場合は通知を送信
            if error_message and self.notifier:
                self._notify_error(error_message, exception, context)
                
            # ドライバーが初期化されている場合は終了
            if self.driver:
                self.logger.info("ブラウザを終了します")
                self.driver.quit()
                self.driver = None
            
        except Exception as e:
            self.logger.error(f"ブラウザの終了中にエラーが発生しました: {str(e)}")
            
    # close() メソッドは quit() のエイリアス
    def close(self, error_message=None, exception=None, context=None):
        """quit()のエイリアス"""
        self.quit(error_message, exception, context)

    def wait_for_element(self, by_or_tuple, value=None, condition=None, timeout=None, visible=False):
        """
        指定された条件で要素を待機する
        
        Args:
            by_or_tuple: By定数またはタプル(group, name)またはタプル(By.XX, value)
            value: セレクタの値（by_or_tupleがBy定数の場合に使用）
            condition: 待機条件。Noneの場合は可視性に応じて選択
            timeout: タイムアウト時間（秒）。未指定時はデフォルトのタイムアウトを使用
            visible: 要素が表示されるのを待つかどうか
            
        Returns:
            WebElement: 見つかった要素。見つからない場合はNone
        """
        try:
            if not self.driver:
                self.logger.error("WebDriverが初期化されていません")
                return None
            
            wait_timeout = timeout or self.timeout
            
            # by_or_tupleの型に応じて処理を分岐
            if isinstance(by_or_tuple, tuple):
                if len(by_or_tuple) == 2:
                    # (group, name)形式の場合
                    if isinstance(by_or_tuple[0], str) and isinstance(by_or_tuple[1], str):
                        group, name = by_or_tuple
                        if not self.selectors:
                            self._load_selectors()
                            
                        if group not in self.selectors or name not in self.selectors[group]:
                            self.logger.error(f"セレクタが見つかりません: {group}.{name}")
                            return None
                        
                        selector_info = self.selectors[group][name]
                        by = self._get_by_type(selector_info['selector_type'])
                        value = selector_info['selector_value']
                        
                        # ログ出力で要素の説明を追加
                        description = selector_info.get('description', '')
                        self.logger.debug(f"要素を待機します: {group}.{name} ({description})")
                    # (By.XX, value)形式の場合
                    else:
                        by, value = by_or_tuple
            else:
                # By定数の場合
                by = by_or_tuple
            
            # 条件が指定されていない場合は、visibleに応じてデフォルト条件を設定
            if condition is None:
                condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
            
            element = WebDriverWait(self.driver, wait_timeout).until(
                condition((by, value))
            )
            return element
            
        except TimeoutException:
            selector_info = f"{by}={value}" if isinstance(by_or_tuple, tuple) else str(by_or_tuple)
            self.logger.warning(f"要素の待機中にタイムアウトが発生しました: {selector_info}, 待機時間: {wait_timeout}秒")
            
            # エラー時のスクリーンショット
            if self.screenshot_on_error:
                self._take_error_screenshot(f"timeout_{selector_info.replace(':', '_').replace('=', '_')}")
                
            return None
        except Exception as e:
            selector_info = f"{by}={value}" if isinstance(by_or_tuple, tuple) else str(by_or_tuple)
            error_message = f"要素の待機中にエラーが発生しました: {selector_info}"
            self._notify_error(error_message, e)
            return None
            
    def analyze_page_content(self, element_filter=None, check_visibility=True):
        """
        現在のページを解析し、重要な要素やステータスを取得する
        
        Args:
            element_filter (dict, optional): 特定の要素タイプのみを解析する場合の設定
                {
                    'forms': True,      # フォーム要素を解析
                    'buttons': True,    # ボタン要素を解析
                    'links': True,      # リンク要素を解析
                    'errors': True,     # エラーメッセージを解析
                    'inputs': True,     # 入力フィールドを解析
                }
            check_visibility (bool): 表示されている要素のみを対象にするかどうか
            
        Returns:
            dict: ページ解析結果を含む辞書
        """
        if not self.driver:
            self.logger.error("WebDriverが初期化されていません")
            return {}
            
        # フィルターの設定
        if element_filter is None:
            element_filter = {
                'forms': True,
                'buttons': True,
                'links': True,
                'errors': True,
                'inputs': True
            }
            
        result = {
            'page_title': self.driver.title,
            'current_url': self.driver.current_url,
            'forms': [],
            'buttons': [],
            'links': [],
            'inputs': [],
            'error_messages': [],
            'alerts': self._check_alerts()
        }
        
        try:
            # ページのステータス情報を取得
            result['page_status'] = self._get_page_status()
            
            # フォーム要素の解析
            if element_filter.get('forms', True):
                form_elements = self.driver.find_elements(By.TAG_NAME, "form")
                for form in form_elements:
                    if not check_visibility or form.is_displayed():
                        form_info = {
                            'id': form.get_attribute('id') or '',
                            'action': form.get_attribute('action') or '',
                            'method': form.get_attribute('method') or 'GET',
                            'is_enabled': True,  # フォーム自体には無効状態がない
                            'element': form  # Selenium WebElement
                        }
                        result['forms'].append(form_info)
            
            # ボタン要素の解析
            if element_filter.get('buttons', True):
                # ボタン要素を取得（button要素とtype="button"のinput要素）
                button_elements = self.driver.find_elements(By.TAG_NAME, "button")
                button_elements.extend(self.driver.find_elements(By.CSS_SELECTOR, "input[type='button'], input[type='submit']"))
                
                for button in button_elements:
                    if not check_visibility or button.is_displayed():
                        button_info = {
                            'id': button.get_attribute('id') or '',
                            'text': button.text or button.get_attribute('value') or '',
                            'type': button.get_attribute('type') or '',
                            'is_enabled': button.is_enabled(),
                            'is_displayed': button.is_displayed(),
                            'element': button  # Selenium WebElement
                        }
                        result['buttons'].append(button_info)
            
            # リンク要素の解析
            if element_filter.get('links', True):
                link_elements = self.driver.find_elements(By.TAG_NAME, "a")
                for link in link_elements:
                    if not check_visibility or link.is_displayed():
                        href = link.get_attribute('href') or ''
                        link_info = {
                            'text': link.text,
                            'href': href,
                            'target': link.get_attribute('target') or '',
                            'is_external': href.startswith(('http', 'https', '//')) and not href.startswith(self.driver.current_url),
                            'is_enabled': link.is_enabled(),
                            'is_displayed': link.is_displayed(),
                            'element': link  # Selenium WebElement
                        }
                        result['links'].append(link_info)
            
            # 入力要素の解析
            if element_filter.get('inputs', True):
                input_selectors = [
                    "input:not([type='hidden'])",
                    "textarea",
                    "select"
                ]
                
                for selector in input_selectors:
                    input_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for input_elem in input_elements:
                        if not check_visibility or input_elem.is_displayed():
                            input_type = input_elem.get_attribute('type') or input_elem.tag_name
                            input_info = {
                                'name': input_elem.get_attribute('name') or '',
                                'id': input_elem.get_attribute('id') or '',
                                'type': input_type,
                                'value': input_elem.get_attribute('value') or '',
                                'placeholder': input_elem.get_attribute('placeholder') or '',
                                'is_required': input_elem.get_attribute('required') == 'true',
                                'is_readonly': input_elem.get_attribute('readonly') == 'true',
                                'is_enabled': input_elem.is_enabled(),
                                'is_displayed': input_elem.is_displayed(),
                                'element': input_elem  # Selenium WebElement
                            }
                            result['inputs'].append(input_info)
            
            # エラーメッセージの解析
            if element_filter.get('errors', True):
                # 一般的なエラーメッセージのセレクタ
                error_selectors = [
                    ".error", ".alert", ".alert-danger", ".alert-error",
                    "[role='alert']", "[class*='error']", "[class*='alert']",
                    ".invalid-feedback", ".text-danger"
                ]
                
                for selector in error_selectors:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for error in error_elements:
                        error_text = error.text.strip()
                        if error_text and (not check_visibility or error.is_displayed()):
                            error_info = {
                                'text': error_text,
                                'is_displayed': error.is_displayed(),
                                'element': error  # Selenium WebElement
                            }
                            result['error_messages'].append(error_info)
            
            return result
            
        except Exception as e:
            self.logger.error(f"ページ解析中にエラーが発生しました: {str(e)}")
            return result

    def _get_page_status(self):
        """
        ページのステータス情報を取得する
            
        Returns:
            dict: ページステータス情報
        """
        status = {
            'ready_state': 'unknown',
            'load_time_ms': 0,
            'dom_content_loaded': False,
            'ajax_requests_active': False,
            'page_interactive': False
        }
        
        try:
            # ページの準備状態
            status['ready_state'] = self.driver.execute_script("return document.readyState")
            
            # ページのロード時間
            timing = self.driver.execute_script(
                "return window.performance && window.performance.timing ? "
                "window.performance.timing.loadEventEnd - window.performance.timing.navigationStart : 0"
            )
            status['load_time_ms'] = timing
            
            # DOMContentLoaded が発火したかどうか
            status['dom_content_loaded'] = self.driver.execute_script(
                "return window.performance && window.performance.timing ? "
                "window.performance.timing.domContentLoadedEventEnd > 0 : false"
            )
            
            # AJAXリクエストがアクティブかどうか
            status['ajax_requests_active'] = self.driver.execute_script(
                "return window.jQuery ? jQuery.active > 0 : false"
            )
            
            # ページがインタラクティブかどうか
            status['page_interactive'] = self.driver.execute_script(
                "return document.readyState === 'interactive' || document.readyState === 'complete'"
            )
            
            return status
            
        except Exception as e:
            self.logger.error(f"ページステータス取得中にエラーが発生しました: {str(e)}")
            return status
    
    def _check_alerts(self):
        """
        現在表示されているアラート/ダイアログを検出して情報を取得する
        
        Returns:
            dict: アラート情報の辞書
                - present: アラートが存在するかどうか
                - text: アラートのテキスト（存在する場合）
                - type: アラートの種類（'alert', 'confirm', 'prompt'のいずれか）
        """
        result = {
            'present': False,
            'text': '',
            'type': 'alert'  # デフォルトのタイプ
        }
        
        try:
            # アラートの存在を確認
            alert = self.driver.switch_to.alert
            
            # アラートのテキストを取得
            alert_text = alert.text
            result['present'] = True
            result['text'] = alert_text
            
            # アラートの種類を推定
            if '?' in alert_text:
                result['type'] = 'confirm'
            elif ':' in alert_text or '入力' in alert_text:
                result['type'] = 'prompt'
            
            self.logger.debug(f"アラート検出: タイプ={result['type']}, テキスト={alert_text}")
            return result
            
        except Exception as e:
            # NoAlertPresentException が投げられるはず
            self.logger.debug("アラートは検出されませんでした")
            return result
        
    def find_element_by_text(self, text, element_types=None, exact_match=False, case_sensitive=True, check_visibility=True):
        """
        指定したテキストを含む要素を検索する
        
        Args:
            text (str): 検索するテキスト
            element_types (list, optional): 検索対象の要素タイプリスト（例: ['a', 'button', 'div']）
            exact_match (bool): 完全一致で検索するかどうか
            case_sensitive (bool): 大文字小文字を区別するかどうか
            check_visibility (bool): 表示されている要素のみを対象にするかどうか
            
        Returns:
            list: 一致する要素のリスト
        """
        if not self.driver:
            self.logger.error("WebDriverが初期化されていません")
            return []
            
        # 検索対象の要素タイプ設定
        if element_types is None:
            element_types = ['a', 'button', 'span', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th']
            
        # 要素タイプをCSSセレクタに変換
        css_selector = ", ".join(element_types)
        
        try:
            # すべての対象要素を取得
            elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            matching_elements = []
            
            # 対応する大文字・小文字処理
            search_text = text if case_sensitive else text.lower()
            
            for element in elements:
                # 表示要素のみをチェック（オプション）
                if check_visibility and not element.is_displayed():
                    continue
                    
                element_text = element.text.strip()
                if not case_sensitive:
                    element_text = element_text.lower()
                
                # テキスト一致の判定
                if (exact_match and element_text == search_text) or \
                   (not exact_match and search_text in element_text):
                    matching_elements.append({
                        'element': element,
                        'text': element.text,
                        'tag': element.tag_name,
                        'is_displayed': element.is_displayed(),
                        'is_enabled': element.is_enabled(),
                        'location': element.location,
                        'size': element.size
                    })
            
            return matching_elements
            
        except Exception as e:
            self.logger.error(f"テキスト検索中にエラーが発生しました: {str(e)}")
            return []
    
    def find_interactive_elements(self, check_visibility=True):
        """
        ページ上のインタラクティブな要素を検索する
        
        Args:
            check_visibility (bool): 表示されている要素のみを対象にするかどうか
            
        Returns:
            dict: タイプ別のインタラクティブ要素リスト
        """
        if not self.driver:
            self.logger.error("WebDriverが初期化されていません")
            return {}
            
        interactive_elements = {
            'clickable': [],  # クリック可能な要素
            'input': [],      # 入力フィールド
            'media': []       # メディア要素
        }
        
        try:
            # クリック可能な要素のセレクタ
            clickable_selectors = [
                "a", "button", "input[type='button']", "input[type='submit']",
                "[onclick]", "[role='button']", "[class*='btn']"
            ]
            
            # 入力フィールドのセレクタ
            input_selectors = [
                "input:not([type='hidden'])", "textarea", "select",
                "[contenteditable='true']"
            ]
            
            # メディア要素のセレクタ
            media_selectors = [
                "video", "audio", "iframe", "canvas"
            ]
            
            # クリック可能な要素を検索
            for selector in clickable_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if not check_visibility or element.is_displayed():
                        interactive_elements['clickable'].append({
                            'element': element,
                            'text': element.text or element.get_attribute('value') or '',
                            'tag': element.tag_name,
                            'is_enabled': element.is_enabled(),
                            'is_displayed': element.is_displayed(),
                            'location': element.location,
                            'size': element.size
                        })
            
            # 入力フィールドを検索
            for selector in input_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if not check_visibility or element.is_displayed():
                        interactive_elements['input'].append({
                            'element': element,
                            'tag': element.tag_name,
                            'type': element.get_attribute('type') or element.tag_name,
                            'name': element.get_attribute('name') or '',
                            'value': element.get_attribute('value') or '',
                            'is_enabled': element.is_enabled(),
                            'is_displayed': element.is_displayed(),
                            'location': element.location,
                            'size': element.size
                        })
            
            # メディア要素を検索
            for selector in media_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if not check_visibility or element.is_displayed():
                        interactive_elements['media'].append({
                            'element': element,
                            'tag': element.tag_name,
                            'src': element.get_attribute('src') or '',
                            'is_displayed': element.is_displayed(),
                            'location': element.location,
                            'size': element.size
                        })
            
            return interactive_elements
            
        except Exception as e:
            self.logger.error(f"インタラクティブ要素検索中にエラーが発生しました: {str(e)}")
            return interactive_elements

    def wait_for_page_load(self, timeout=None):
        """
        ページの読み込みが完了するのを待機する
        
        Args:
            timeout (int, optional): タイムアウト秒数。デフォルトはインスタンス初期化時の値
            
        Returns:
            bool: 成功した場合はTrue
        """
        if not self.driver:
            self.logger.error("WebDriverが初期化されていません")
            return False
            
        if timeout is None:
            timeout = int(self._get_config_value("BROWSER", "page_load_timeout", "30"))
            
        try:
            # document.readyStateがcompleteになるまで待機
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # JavaScriptによる非同期処理の完了を確認（オプション）
            try:
                self.driver.execute_script("return (typeof jQuery === 'undefined' || jQuery.active === 0)")
            except:
                pass  # jQueryが未定義の場合は無視
            
            self.logger.info("ページ読み込みが完了しました")
            return True
        except Exception as e:
            self.logger.warning(f"ページ読み込み待機中にエラーが発生しました: {str(e)}")
            return False

    def switch_to_new_window(self, current_handles=None, timeout=10, retries=3):
        """
        新しく開いたウィンドウに切り替える
        
        Args:
            current_handles (list, optional): 切り替え前のウィンドウハンドルリスト
            timeout (int, optional): 新しいウィンドウが開くまで待機する時間(秒)
            retries (int, optional): 失敗時のリトライ回数
        
        Returns:
            bool: 切り替えが成功した場合はTrue、失敗した場合はFalse
        """
        if not self.driver:
            self.logger.error("WebDriverが初期化されていません")
            return False
            
        # 現在のウィンドウハンドルが指定されていない場合は取得
        if current_handles is None:
            try:
                current_handles = self.driver.window_handles
                self.logger.info(f"現在のウィンドウハンドル: {current_handles}")
            except Exception as e:
                self.logger.error(f"現在のウィンドウハンドルの取得に失敗しました: {str(e)}")
                return False
        
        retry_count = 0
        while retry_count < retries:
            try:
                # 新しいウィンドウが開くまで待機
                start_time = time.time()
                new_handle = None
                
                while time.time() - start_time < timeout:
                    try:
                        # 現在のハンドルを再取得（セッションが無効になっていないか確認）
                        handles = self.driver.window_handles
                        
                        # 新しいウィンドウを探す
                        for handle in handles:
                            if handle not in current_handles:
                                new_handle = handle
                                break
                        
                        if new_handle:
                            break
                            
                        time.sleep(0.5)  # 短い間隔で再試行
                    except Exception as inner_e:
                        self.logger.warning(f"ウィンドウハンドルの取得中にエラーが発生しました（リトライ中）: {str(inner_e)}")
                        time.sleep(1)
                        continue
                
                if not new_handle:
                    self.logger.warning(f"新しいウィンドウが見つかりませんでした（{timeout}秒待機後）")
                    # スクリーンショットを撮影してエラーを記録
                    self.save_screenshot(f"window_switch_timeout_{retry_count}.png")
                    retry_count += 1
                    time.sleep(1)  # リトライ前に待機
                    continue
                
                # 新しいウィンドウに切り替え
                self.driver.switch_to.window(new_handle)
                
                # 切り替え後のURLを表示
                self.logger.info(f"新しいウィンドウに切り替えました: {self.driver.current_url}")
                
                # 切り替え後のスクリーンショット
                self.save_screenshot("after_window_switch.png")
                
                return True
                
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"新しいウィンドウへの切り替え中にエラーが発生しました (リトライ {retry_count}/{retries}): {str(e)}")
                
                if retry_count >= retries:
                    self.logger.error(f"新しいウィンドウへの切り替えに失敗しました（{retries}回リトライ後）")
                    self.save_screenshot("window_switch_error.png")
                    return False
                
                # リトライ前に待機
                time.sleep(2)
        
        return False

    def get_page_source(self):
        """
        現在のページのHTMLソースを取得する
        
        Returns:
            str: HTMLソース。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                self.logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.page_source
        except Exception as e:
            error_message = "ページソース取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def get_current_url(self):
        """
        現在のURLを取得する

        Returns:
            str: 現在のURL
        """
        try:
            return self.driver.current_url
        except Exception as e:
            self.logger.error(f"現在のURLの取得に失敗しました: {str(e)}")
            return None
            
    def detect_page_changes(self, wait_seconds=3):
        """
        ページの状態変化を検出します。
        ダウンロード開始やAJAXリクエストによる変更を検出するために使用します。
        
        Args:
            wait_seconds (int): 変化を待機する最大秒数
            
        Returns:
            bool: 変化が検出された場合はTrue
        """
        try:
            # 初期状態を記録
            initial_state_script = """
                return {
                    height: document.body.scrollHeight,
                    elements: document.querySelectorAll('*').length,
                    text: document.body.textContent.length,
                    activeXHR: false
                };
            """
            initial_state = self.driver.execute_script(initial_state_script)
            
            # 現在アクティブなXHRがないか確認するスクリプト
            xhr_check_script = """
                if (window.performance && window.performance.getEntries) {
                    var entries = window.performance.getEntries();
                    var now = new Date().getTime();
                    for (var i = 0; i < entries.length; i++) {
                        var entry = entries[i];
                        if (entry.entryType === 'resource' && 
                            now - entry.startTime < 3000 &&
                            !entry.responseEnd) {
                            return true;  // アクティブなXHRがある
                        }
                    }
                }
                return false;
            """
            
            start_time = time.time()
            while time.time() - start_time < wait_seconds:
                # 現在の状態を取得
                current_state = self.driver.execute_script(initial_state_script)
                
                # XHRの状態を確認
                xhr_active = self.driver.execute_script(xhr_check_script)
                
                # 状態変化を検出
                if (current_state['height'] != initial_state['height'] or
                    abs(current_state['elements'] - initial_state['elements']) > 5 or
                    abs(current_state['text'] - initial_state['text']) > 20 or
                    xhr_active):
                    return True
                
                time.sleep(0.2)
            
            return False
            
        except Exception as e:
            self.logger.warning(f"ページ変更検出中にエラーが発生しました: {str(e)}")
            return False 

    def _analyze_page_details(self, soup):
        """
        ページの詳細情報を分析する
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            dict: 詳細な解析結果を含む辞書
        """
        details = {
            'all_headings': {},  # 見出しの階層構造
            'forms': [],         # フォーム情報
            'tables': [],        # テーブル情報
            'links': [],         # リンク一覧
            'images': [],        # 画像一覧
            'meta_tags': {}      # メタタグ情報
        }
        
        # 見出し階層の取得
        for level in range(1, 7):
            headings = soup.find_all(f'h{level}')
            if headings:
                details['all_headings'][f'h{level}'] = [h.text.strip() for h in headings]
        
        # フォーム情報の取得
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            form_info = {
                'id': form.get('id', f'unnamed_form_{i}'),
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'inputs': []
            }
            
            # フォーム内の入力要素を取得
            inputs = form.find_all(['input', 'select', 'textarea'])
            for inp in inputs:
                input_type = inp.name
                if input_type == 'input':
                    input_type = inp.get('type', 'text')
                
                input_info = {
                    'type': input_type,
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'placeholder': inp.get('placeholder', ''),
                    'required': 'required' in inp.attrs or inp.get('required') == True
                }
                form_info['inputs'].append(input_info)
            
            details['forms'].append(form_info)
        
        # テーブル情報の取得
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            table_info = {
                'id': table.get('id', f'unnamed_table_{i}'),
                'headers': [],
                'rows': 0,
                'columns': 0
            }
            
            # テーブルヘッダーを取得
            th_elements = table.find_all('th')
            if th_elements:
                table_info['headers'] = [th.text.strip() for th in th_elements]
            
            # 行数を取得
            rows = table.find_all('tr')
            table_info['rows'] = len(rows)
            
            # 列数を推定（最初の行から）
            if rows and not th_elements:
                first_row_cells = rows[0].find_all(['td', 'th'])
                table_info['columns'] = len(first_row_cells)
            else:
                table_info['columns'] = len(th_elements) if th_elements else 0
                
            details['tables'].append(table_info)
        
        # リンク情報の収集
        links = soup.find_all('a', href=True)
        for link in links:
            link_info = {
                'text': link.text.strip(),
                'url': link['href'],
                'title': link.get('title', ''),
                'is_external': link['href'].startswith(('http', 'https', '//'))
            }
            details['links'].append(link_info)
        
        # 画像情報の収集
        images = soup.find_all('img')
        for img in images:
            img_info = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            }
            details['images'].append(img_info)
        
        # メタタグ情報の収集
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', meta.get('property', ''))
            if name:
                details['meta_tags'][name] = meta.get('content', '')
        
        return details 

    def find_element(self, by, value, timeout=None):
        """
        指定したロケーターに一致する要素を検索する
        
        Args:
            by (By): 要素の検索方法（By.ID, By.CSS_SELECTOR など）
            value (str): セレクタの値
            timeout (int, optional): タイムアウト（秒）。省略時はデフォルト値を使用
            
        Returns:
            WebElement or None: 見つかった要素、見つからない場合はNone
        """
        wait_timeout = timeout or self.timeout
        try:
            # 要素を明示的に待機して検索
            wait = WebDriverWait(self.driver, wait_timeout)
            element = wait.until(
                EC.presence_of_element_located((by, value))
            )
            self.logger.debug(f"要素を検出しました: {by}={value}")
            return element
        except TimeoutException:
            self.logger.warning(f"要素が見つかりませんでした: {by}={value}")
            return None
        except Exception as e:
            self.logger.error(f"要素検索中にエラーが発生しました: {str(e)}")
            return None 