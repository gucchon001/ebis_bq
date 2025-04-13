"""
ブラウザ操作の基本機能を提供するモジュール
"""
import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.environment import env
from src.utils.logging_config import get_logger

class BrowserOperation:
    """ブラウザ操作の基本機能を提供するクラス"""

    # セレクタタイプとByクラスのマッピング
    SELECTOR_MAP = {
        'id': By.ID,
        'css': By.CSS_SELECTOR,
        'xpath': By.XPATH,
        'name': By.NAME,
        'class': By.CLASS_NAME,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT,
        'tag': By.TAG_NAME
    }

    def __init__(self):
        """初期化処理"""
        self.logger = get_logger(__name__)
        self.selectors = None
        self._initialize_browser()
        self._load_selectors()

    def _initialize_browser(self):
        """ブラウザを初期化する"""
        try:
            chrome_options = Options()
            
            # ヘッドレスモードの設定
            headless = env.get_config_value("BROWSER", "headless", "false").lower() == "true"
            if headless:
                chrome_options.add_argument("--headless=new")
                self.logger.info("ヘッドレスモードで実行します")
            
            # ウィンドウサイズの設定
            window_width = int(env.get_config_value("BROWSER", "window_width", "1366"))
            window_height = int(env.get_config_value("BROWSER", "window_height", "768"))
            chrome_options.add_argument(f"--window-size={window_width},{window_height}")
            
            # 追加設定
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # パスワードの自動入力を無効化
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            })
            
            # WebDriverの初期化
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # タイムアウトの設定
            page_load_timeout = int(env.get_config_value("BROWSER", "page_load_timeout", "30"))
            self.driver.set_page_load_timeout(page_load_timeout)
            
            # 要素検索のデフォルトタイムアウト
            self.timeout = int(env.get_config_value("BROWSER", "timeout", "10"))
            
            self.logger.info("ブラウザを初期化しました")
            
        except Exception as e:
            self.logger.error(f"ブラウザの初期化に失敗しました: {str(e)}", exc_info=True)
            raise

    def _load_selectors(self):
        """セレクタをCSVファイルから読み込む"""
        try:
            selector_file = env.resolve_path("config/selectors.csv")
            self.logger.debug(f"セレクタCSVを読み込みます: {selector_file}")
            print(f"セレクタCSVを読み込みます: {selector_file}")
            
            # ファイルの存在確認
            if not os.path.exists(selector_file):
                error_msg = f"セレクタファイルが存在しません: {selector_file}"
                self.logger.error(error_msg)
                print(error_msg)
                raise FileNotFoundError(error_msg)
            
            selectors = {}
            
            with open(selector_file, 'r', encoding='utf-8') as file:
                # ファイルの先頭行を確認
                first_line = file.readline()
                print(f"セレクタCSVの先頭行: {first_line}")
                
                # ファイルポインタを先頭に戻す
                file.seek(0)
                
                reader = csv.DictReader(file)
                for row in reader:
                    # コメント行をスキップ
                    if row['group'].startswith('#'):
                        continue
                        
                    # グループごとに辞書に格納
                    group = row['group']
                    name = row['name']
                    selector_type = row['selector_type']
                    selector_value = row['selector_value']
                    
                    print(f"セレクタ読み込み: group={group}, name={name}, type={selector_type}")
                    
                    if group not in selectors:
                        selectors[group] = {}
                        
                    selectors[group][name] = {
                        'type': selector_type,
                        'value': selector_value
                    }
            
            self.selectors = selectors
            self.logger.info(f"セレクタを読み込みました: {len(selectors)} グループ")
            print(f"セレクタを読み込みました: {len(selectors)} グループ")
            
            # ログインセレクタが存在するか確認
            if 'login' in selectors:
                print(f"ログインセレクタ: {selectors['login'].keys()}")
            else:
                print("警告: ログインセレクタが見つかりません")
                
            return selectors
            
        except Exception as e:
            error_msg = f"セレクタCSVの読み込みに失敗しました: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise

    def get_selector(self, group, name):
        """
        指定されたグループと名前に基づいてセレクタを取得する
        
        Args:
            group (str): セレクタのグループ名（例: login, detailed_analysis）
            name (str): セレクタの要素名（例: username, password）
            
        Returns:
            tuple: (セレクタタイプ, セレクタ値) のタプル
        """
        try:
            # セレクタが読み込まれていない場合は読み込む
            if self.selectors is None:
                self._load_selectors()
                
            # 指定されたグループと名前のセレクタを取得
            if group in self.selectors and name in self.selectors[group]:
                selector = self.selectors[group][name]
                return (selector['type'], selector['value'])
                
            # セレクタが見つからない場合はエラーを出力
            self.logger.error(f"セレクタが見つかりません: group={group}, name={name}")
            raise ValueError(f"セレクタが見つかりません: group={group}, name={name}")
            
        except Exception as e:
            self.logger.error(f"セレクタの取得に失敗しました: {str(e)}", exc_info=True)
            raise

    def wait_for_element(self, selector_type, selector_value, timeout=None):
        """
        指定されたセレクタで要素が見つかるまで待機する
        
        Args:
            selector_type (str): セレクタタイプ（id, css, xpathなど）
            selector_value (str): セレクタ値
            timeout (int, optional): タイムアウト時間（秒）
            
        Returns:
            WebElement: 見つかった要素
        """
        try:
            wait_timeout = timeout if timeout is not None else self.timeout
            by_type = self.SELECTOR_MAP.get(selector_type, By.CSS_SELECTOR)
            
            self.logger.debug(f"要素を待機中: {selector_type}={selector_value} (タイムアウト: {wait_timeout}秒)")
            element = WebDriverWait(self.driver, wait_timeout).until(
                EC.presence_of_element_located((by_type, selector_value))
            )
            
            return element
            
        except TimeoutException:
            self.logger.error(f"要素が見つかりませんでした: {selector_type}={selector_value}")
            self._take_screenshot(f"element_not_found_{selector_type}_{selector_value}")
            raise
        except Exception as e:
            self.logger.error(f"要素待機中にエラーが発生しました: {str(e)}", exc_info=True)
            raise

    def wait_for_clickable(self, selector_type, selector_value, timeout=None):
        """
        指定されたセレクタで要素がクリック可能になるまで待機する
        
        Args:
            selector_type (str): セレクタタイプ（id, css, xpathなど）
            selector_value (str): セレクタ値
            timeout (int, optional): タイムアウト時間（秒）
            
        Returns:
            WebElement: クリック可能な要素
        """
        try:
            wait_timeout = timeout if timeout is not None else self.timeout
            by_type = self.SELECTOR_MAP.get(selector_type, By.CSS_SELECTOR)
            
            self.logger.debug(f"クリック可能な要素を待機中: {selector_type}={selector_value} (タイムアウト: {wait_timeout}秒)")
            element = WebDriverWait(self.driver, wait_timeout).until(
                EC.element_to_be_clickable((by_type, selector_value))
            )
            
            return element
            
        except TimeoutException:
            self.logger.error(f"クリック可能な要素が見つかりませんでした: {selector_type}={selector_value}")
            self._take_screenshot(f"element_not_clickable_{selector_type}_{selector_value}")
            raise
        except Exception as e:
            self.logger.error(f"クリック可能な要素の待機中にエラーが発生しました: {str(e)}", exc_info=True)
            raise

    def _take_screenshot(self, filename):
        """
        スクリーンショットを保存する
        
        Args:
            filename (str): ファイル名（拡張子なし）
        """
        try:
            # スクリーンショットが有効な場合のみ実行
            if env.get_config_value("BROWSER", "screenshot_on_error", "true").lower() == "true":
                screenshot_dir = env.get_config_value("BROWSER", "screenshot_dir", "logs/screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)
                
                # 現在のタイムスタンプを含めたファイル名
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(screenshot_dir, f"{timestamp}_{filename}.png")
                
                # スクリーンショットを保存
                self.driver.save_screenshot(filepath)
                self.logger.info(f"スクリーンショットを保存しました: {filepath}")
                
                return filepath
                
        except Exception as e:
            self.logger.error(f"スクリーンショットの保存に失敗しました: {str(e)}")
            return None

    def _handle_error(self, error_type, context):
        """
        エラー処理の共通メソッド
        
        Args:
            error_type (str): エラーの種類
            context (dict): エラー発生時のコンテキスト情報
        """
        try:
            self.logger.error(f"エラーが発生しました: {error_type}")
            self.logger.error(f"エラーコンテキスト: {context}")
            
            # スクリーンショットを取得
            self._take_screenshot(f"error_{error_type}")
            
        except Exception as e:
            self.logger.error(f"エラー処理中にさらにエラーが発生しました: {str(e)}")

    def __del__(self):
        """終了処理"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                self.logger.info("ブラウザを終了しました")
        except Exception as e:
            self.logger.error(f"ブラウザの終了に失敗しました: {str(e)}") 