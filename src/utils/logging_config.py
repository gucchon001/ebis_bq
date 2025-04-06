#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ロギング設定を管理するモジュール

アプリケーション全体で一貫したロギングを提供します。
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.utils.environment import env  # 追加: env をインポート
import os
import sys

class LoggingConfig:
    _initialized = False

    def __init__(self):
        """
        ログ設定を初期化します。
        """
        if LoggingConfig._initialized:
            return  # 再初期化を防止

        # ログディレクトリはプロジェクトルートからの相対パス
        self.log_dir = Path("logs")
        
        # 設定ファイルからログレベルを取得
        log_level_str = env.get_log_level()
        
        # 文字列からログレベルに変換
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self.log_level = log_level_map.get(log_level_str, logging.INFO)
        
        self.log_format = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

        self.setup_logging()

        LoggingConfig._initialized = True  # 初期化済みフラグを設定

    def setup_logging(self) -> None:
        """
        ロギング設定をセットアップします。
        日単位でログファイルを作成します。
        """
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # 日付を含んだログファイル名を作成
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"app_{today}.log"

        handlers = [
            # ファイルハンドラ - 日付入りのファイル名で保存
            logging.FileHandler(
                log_file, mode='a', encoding="utf-8"
            ),
            # 標準出力ハンドラ
            logging.StreamHandler(),
        ]

        logging.basicConfig(
            level=self.log_level,
            format=self.log_format,
            handlers=handlers,
        )

        logging.getLogger().info(f"Logging setup complete. Log file: {log_file}")
        logging.getLogger().info(f"Log level: {logging.getLevelName(self.log_level)}")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    名前付きロガーを取得します。

    Args:
        name (Optional[str]): ロガー名

    Returns:
        logging.Logger: 名前付きロガー
    """
    LoggingConfig()
    return logging.getLogger(name)

def setup_logging(level=None, log_file=None):
    """
    ロギングのセットアップを行う
    
    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: ログファイルのパス
    """
    # デフォルトのログレベル
    if level is None:
        level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # ログレベルの文字列を対応する定数に変換
    numeric_level = getattr(logging, level, None)
    if not isinstance(numeric_level, int):
        # 無効なログレベルが指定された場合はINFOを使用
        numeric_level = logging.INFO
    
    # ログフォーマット
    log_format = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Windows環境での文字化け対策
    if sys.platform.startswith('win'):
        import codecs
        # Python 3.7以降では reconfigure メソッドが利用可能
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
            sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
        else:
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'backslashreplace')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'backslashreplace')
            
        # コンソールのコードページを変更 (CP65001 = UTF-8)
        try:
            os.system('chcp 65001 > NUL')
        except:
            pass
    
    # 既存のハンドラをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # コンソール出力用のハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(log_format, date_format)
    # エンコーディングエラー時の処理設定
    if hasattr(console_handler, 'setStream'):
        console_handler.setStream(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ログファイル出力用のハンドラ（指定されていない場合は自動的に生成）
    if log_file is None:
        # logsディレクトリを作成
        logs_dir = resolve_path('logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # 日付ベースのログファイル名
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(logs_dir, f'app_{today}.log')
    
    # ファイルハンドラの設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(numeric_level)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 設定完了のログ
    root_logger.info(f'Logging setup complete. Log file: {log_file}')
    root_logger.info(f'Log level: {level}')

def resolve_path(path):
    """相対パスを絶対パスに変換"""
    if os.path.isabs(path):
        return path
    return os.path.join(env.get_project_root(), path)