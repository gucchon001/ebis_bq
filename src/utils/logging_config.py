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
import os
import sys
from logging.handlers import RotatingFileHandler
from src.utils.environment import EnvironmentUtils

# ロギング設定が完了したかどうかのフラグ
_is_initialized = False

def get_logger(name: str) -> logging.Logger:
    """
    ロガーインスタンスを取得

    Args:
        name (str): ロガー名（通常は__name__）

    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    global _is_initialized
    if not _is_initialized:
        _setup_logging()
        _is_initialized = True
    return logging.getLogger(name)

def _setup_logging():
    """ロギング設定の初期化"""
    # 既に初期化されている場合は何もしない
    global _is_initialized
    if _is_initialized:
        return
        
    # 環境設定の読み込み
    env = EnvironmentUtils()
    log_level = env.get_log_level()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # ログディレクトリの作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # ログファイル名の生成（日付とプロセスIDを含む）
    today = datetime.now().strftime("%Y%m%d")
    pid = os.getpid()
    log_file = log_dir / f"app_{today}_{pid}.log"

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 既存のハンドラをクリア
    root_logger.handlers.clear()

    # フォーマッタの設定
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ファイルハンドラの設定
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    root_logger.addHandler(file_handler)

    # コンソールハンドラの設定（INFO以上のみ）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # 特定のロガーのレベル設定
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)

    # Windows環境での文字化け対策
    if sys.platform.startswith('win'):
        import codecs
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
            sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
        else:
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'backslashreplace')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'backslashreplace')
        try:
            os.system('chcp 65001 > NUL')
        except:
            pass