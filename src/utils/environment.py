"""
環境変数と設定ファイルを管理するモジュール
"""
import os
import configparser
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any

class EnvironmentUtils:
    """環境変数と設定ファイルを管理するクラス"""

    def __init__(self):
        """初期化処理"""
        self.config = configparser.ConfigParser()
        self.load_env()
        self.load_config()

    def load_env(self):
        """環境変数をロード"""
        env_path = Path("config/secrets.env")
        if env_path.exists():
            load_dotenv(env_path)
            print(f"環境変数ファイルをロードしました: {env_path}")
        else:
            error_msg = f"環境変数ファイル config/secrets.env が見つかりません: {os.path.abspath(env_path)}"
            print(error_msg)
            raise FileNotFoundError(error_msg)

    def load_config(self):
        """設定ファイルをロード"""
        config_path = Path("config/settings.ini")
        if config_path.exists():
            self.config.read(config_path, encoding='utf-8')
            print(f"設定ファイルをロードしました: {config_path}")
        else:
            error_msg = f"設定ファイル config/settings.ini が見つかりません: {os.path.abspath(config_path)}"
            print(error_msg)
            raise FileNotFoundError(error_msg)

    def get_env_var(self, var_name: str, default: str = None) -> str:
        """
        環境変数を取得

        Args:
            var_name (str): 環境変数名
            default (str, optional): デフォルト値

        Returns:
            str: 環境変数の値
        """
        value = os.getenv(var_name, default)
        if value is None:
            raise ValueError(f"環境変数 {var_name} が設定されていません")
        return value

    def get_config_value(self, section: str, key: str, default: str = None) -> str:
        """
        設定値を取得

        Args:
            section (str): セクション名
            key (str): キー名
            default (str, optional): デフォルト値

        Returns:
            str: 設定値
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                return default
            raise ValueError(f"設定値 [{section}]{key} が見つかりません")

    def get_project_root(self) -> Path:
        """
        プロジェクトのルートディレクトリを取得します。

        Returns:
            Path: プロジェクトのルートディレクトリ
        """
        return Path(__file__).resolve().parent.parent.parent

    def resolve_path(self, relative_path: str) -> str:
        """
        相対パスを絶対パスに解決します。

        Args:
            relative_path (str): 相対パス

        Returns:
            str: 絶対パス
        """
        if os.path.isabs(relative_path):
            return relative_path
        
        project_root = self.get_project_root()
        return os.path.join(project_root, relative_path)

    def get_environment(self) -> str:
        """
        現在の環境を取得します。
        デフォルト値は 'development' です。

        Returns:
            str: 現在の環境（例: 'development', 'production'）
        """
        return self.get_env_var("APP_ENV", "development")

    def get_log_level(self) -> str:
        """
        ログレベルを取得します。
        環境変数から取得できない場合は、環境設定から取得します。
        
        Returns:
            str: ログレベル（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）
        """
        # 環境変数から直接ログレベルが指定されている場合
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            return log_level
        
        # 現在の環境を取得
        environment = self.get_environment()
        
        # 環境に応じたログレベルを設定ファイルから取得
        try:
            if environment == "development":
                return self.get_config_value("development", "LOG_LEVEL", "DEBUG")
            elif environment == "production":
                return self.get_config_value("production", "LOG_LEVEL", "WARNING")
        except:
            pass  # 設定がない場合はデフォルト値を使用
        
        # デフォルト値
        return "INFO"


# EnvironmentUtils クラスを env としてインスタンス化
# これにより、from src.utils.environment import env として使用できる
env = EnvironmentUtils()

print("EnvironmentUtilsクラスがインスタンス化されました")
