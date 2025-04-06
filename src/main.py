#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
メインモジュール
"""

import sys
import logging
from pathlib import Path
from src.utils.logging_config import get_logger
from src.utils.environment import env  # 追加: env をインポート

# ロガーの取得
logger = get_logger(__name__)

def setup():
    """
    アプリケーションのセットアップを行います。
    """
    logger.info("アプリケーションをセットアップしています...")
    
    # 環境情報のログ出力
    current_env = env.get_environment()
    logger.info(f"実行環境: {current_env}")
    
    # ログレベルの取得と設定
    log_level = env.get_log_level()
    logger.info(f"ログレベル: {log_level}")
    
    # 環境設定からデバッグモードを取得
    debug_mode = env.get_config_value(current_env, "DEBUG", False)
    logger.info(f"デバッグモード: {debug_mode}")
    
    return True

def main():
    """
    メイン処理を実行します。
    """
    if not setup():
        logger.error("セットアップに失敗しました。")
        return 1

    logger.info("処理を開始します...")
    
    # ここにメイン処理を記述
    
    logger.info("処理が完了しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
