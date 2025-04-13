"""
アドエビスのログインページ操作を提供するモジュール
"""
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.environment import env
from src.utils.logging_config import get_logger
from .browser_operation＿＿＿＿ import BrowserOperation
import time

class LoginPage(BrowserOperation):
    """ログインページの操作を提供するクラス"""

    def __init__(self):
        """初期化処理"""
        super().__init__()
        self.logger = get_logger(__name__)

    def login(self) -> bool:
        """
        ログイン処理を実行

        Returns:
            bool: ログイン成功時True、失敗時False
        """
        try:
            # ログインページにアクセス
            login_url = env.get_config_value("LOGIN", "url")
            self.logger.info(f"ログインページにアクセス: {login_url}")
            self.driver.get(login_url)

            # アカウントキーの入力
            account_key = env.get_env_var("EBIS_ACCOUNT_KEY")
            self.logger.debug("アカウントキー入力欄を待機")
            selector_type, selector_value = self.get_selector('login', 'account_key')
            account_key_element = self.wait_for_element(selector_type, selector_value)
            account_key_element.send_keys(account_key)

            # ユーザー名の入力
            username = env.get_env_var("EBIS_USERNAME")
            self.logger.debug("ユーザー名入力欄を待機")
            selector_type, selector_value = self.get_selector('login', 'username')
            username_element = self.wait_for_element(selector_type, selector_value)
            username_element.send_keys(username)

            # パスワードの入力
            password = env.get_env_var("EBIS_PASSWORD")
            # パスワードの値を確認（セキュリティのために一部のみ表示）
            if password and len(password) > 4:
                mask_password = password[:2] + "*" * (len(password) - 4) + password[-2:]
            else:
                mask_password = "***" if password else "なし"
            self.logger.debug(f"設定するパスワード（マスク）: {mask_password}")
            self.logger.debug("パスワード入力欄を待機")
            selector_type, selector_value = self.get_selector('login', 'password')
            password_element = self.wait_for_element(selector_type, selector_value)
            
            # 既存の入力をクリアして新しいパスワードを設定
            password_element.clear()
            time.sleep(0.5)  # クリア後少し待機
            password_element.send_keys(password)

            # 実際に入力されたパスワードの確認（セキュリティのため文字数のみ）
            try:
                actual_password = password_element.get_attribute("value")
                self.logger.debug(f"パスワードフィールドの文字数: {len(actual_password)}文字")
                if password != actual_password:
                    self.logger.warning("期待したパスワードと実際の入力値が異なります")
            except Exception as e:
                self.logger.warning(f"パスワード入力値の確認でエラー: {str(e)}")

            # ログインボタンのクリック
            self.logger.debug("ログインボタンを待機")
            selector_type, selector_value = self.get_selector('login', 'login_button')
            login_button = self.wait_for_clickable(selector_type, selector_value)
            login_button.click()

            # ログイン成功の確認
            success = self.validate_login_success()
            if success:
                self.logger.info("ログイン成功")
                # ポップアップ処理
                self.handle_popup()
                return True
            else:
                self.logger.error("ログイン失敗")
                return False

        except Exception as e:
            self.logger.error(f"ログイン処理でエラー発生: {str(e)}", exc_info=True)
            self._handle_error("login_error", {
                "url": login_url,
                "error": str(e)
            })
            return False

    def validate_login_success(self) -> bool:
        """
        ログイン成功を確認

        Returns:
            bool: ログイン成功時True、失敗時False
        """
        try:
            # 成功URLの取得
            success_url = env.get_config_value("LOGIN", "success_url")
            redirect_timeout = int(env.get_config_value("LOGIN", "redirect_timeout", "10"))

            # リダイレクト待機
            self.logger.debug(f"リダイレクト待機: {success_url}")
            WebDriverWait(self.driver, redirect_timeout).until(
                lambda driver: success_url in driver.current_url
            )

            return True

        except TimeoutException:
            self.logger.error("ログイン後のリダイレクトタイムアウト")
            return False
        except Exception as e:
            self.logger.error(f"ログイン成功確認でエラー: {str(e)}")
            return False

    def handle_popup(self):
        """ログイン後のポップアップを処理"""
        try:
            # ポップアップの待機と閉じるボタンのクリック
            self.logger.debug("ポップアップ閉じるボタンを待機")
            selector_type, selector_value = self.get_selector('popup', 'login_notice')
            popup_close_button = self.wait_for_clickable(selector_type, selector_value)
            popup_close_button.click()
            self.logger.info("ログイン後のポップアップを閉じました")

        except TimeoutException:
            self.logger.debug("ポップアップは表示されませんでした")
        except Exception as e:
            self.logger.warning(f"ポップアップ処理でエラー: {str(e)}") 