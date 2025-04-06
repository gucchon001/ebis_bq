import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any
import configparser

class EnvironmentUtils:
    """プロジェクト全体で使用する環境関連のユーティリティクラス"""

    # プロジェクトルートのデフォルト値
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def get_project_root() -> Path:
        """
        プロジェクトのルートディレクトリを取得します。

        Returns:
            Path: プロジェクトのルートディレクトリ
        """
        return EnvironmentUtils.BASE_DIR

    @staticmethod
    def load_env(env_file: Optional[Path] = None) -> None:
        """
        環境変数を .env ファイルからロードします。

        Args:
            env_file (Optional[Path]): .env ファイルのパス
        """
        env_file = env_file or (EnvironmentUtils.BASE_DIR / "config" / "secrets.env")

        if not env_file.exists():
            raise FileNotFoundError(f"{env_file} が見つかりません。正しいパスを指定してください。")

        load_dotenv(env_file)

    @staticmethod
    def get_env_var(key: str, default: Optional[Any] = None) -> Any:
        """
        環境変数を取得します。

        Args:
            key (str): 環境変数のキー
            default (Optional[Any]): デフォルト値

        Returns:
            Any: 環境変数の値またはデフォルト値
        """
        return os.getenv(key, default)

    @staticmethod
    def get_config_value(section: str, key: str, default: Optional[Any] = None) -> Any:
        """
        設定ファイルから指定のセクションとキーの値を取得します。

        Args:
            section (str): セクション名
            key (str): キー名
            default (Optional[Any]): デフォルト値

        Returns:
            Any: 設定値
        """
        config_path = EnvironmentUtils.BASE_DIR / "config" / "settings.ini"
        
        if not config_path.exists():
            return default
            
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')

        if not config.has_section(section):
            return default
        if not config.has_option(section, key):
            return default

        value = config.get(section, key, fallback=default)

        # 型変換
        if value.isdigit():
            return int(value)
        if value.replace('.', '', 1).isdigit():
            return float(value)
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        return value

    @staticmethod
    def get_environment() -> str:
        """
        環境変数 APP_ENV を取得します。
        デフォルト値は 'development' です。

        Returns:
            str: 現在の環境（例: 'development', 'production'）
        """
        return EnvironmentUtils.get_env_var("APP_ENV", "development")

    @staticmethod
    def get_log_level() -> str:
        """
        ログレベルを取得します。
        環境変数から取得できない場合は、環境設定から取得します。
        
        Returns:
            str: ログレベル（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）
        """
        # 環境変数から直接ログレベルが指定されている場合
        log_level = EnvironmentUtils.get_env_var("LOG_LEVEL")
        if log_level:
            return log_level
        
        # 現在の環境を取得
        environment = EnvironmentUtils.get_environment()
        
        # 環境に応じたログレベルを設定ファイルから取得
        if environment == "development":
            return EnvironmentUtils.get_config_value("development", "LOG_LEVEL", "DEBUG")
        elif environment == "production":
            return EnvironmentUtils.get_config_value("production", "LOG_LEVEL", "WARNING")
        
        # デフォルト値
        return "INFO"


# EnvironmentUtils クラスを env としてエクスポート
# これにより、from src.utils.environment import env として使用できる
env = EnvironmentUtils

# 初期化時に環境変数を自動で読み込む
try:
    env.load_env()
except FileNotFoundError:
    pass  # 設定ファイルがない場合はスキップ
