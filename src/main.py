#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
メインモジュール

Ad Ebisの詳細分析CSVとコンバージョン属性レポートCSVをダウンロードするメインプログラムです。
このモジュールは、全体のフローを制御し、各機能モジュールを呼び出す役割を担います。

処理フロー:
1. 環境設定の読み込み
2. ブラウザの初期化
3. ログイン処理（login_page.py）
4. 詳細分析CSVダウンロード（csv_downloader.py）
5. コンバージョン属性レポートCSVダウンロード（csv_downloader.py）
"""

import sys
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta
import traceback

from src.utils.logging_config import get_logger
from src.utils.environment import env
from src.modules.selenium.browser import Browser
from src.modules.ebis.login_page import EbisLoginPage, LoginError
from src.modules.ebis.csv_downloader import EbisCSVDownloader, CSVDownloadError

# ロガーの初期化（プログラム開始時に1回だけ実行）
logger = get_logger(__name__)

def parse_args():
    """コマンドライン引数をパースします"""
    parser = argparse.ArgumentParser(description="Ad Ebis CSVダウンロード")
    parser.add_argument('--headless', help='ヘッドレスモードで実行', action='store_true')
    parser.add_argument('--start', help='開始日（YYYY-MM-DD形式）', default=None)
    parser.add_argument('--end', help='終了日（YYYY-MM-DD形式）', default=None)
    parser.add_argument('--download-dir', help='ダウンロードディレクトリ', default="data/downloads")
    parser.add_argument('--type', help='ダウンロードするレポートの種類（detailed_analysis, cv_attribute, all）', 
                       default="all", choices=["detailed_analysis", "cv_attribute", "all"])
    
    return parser.parse_args()

def initialize_environment() -> bool:
    """環境を初期化します"""
    try:
        # 環境変数のロード
        env.load_env()
        logger.info("環境変数をロードしました")
        
        # 環境情報の取得
        current_env = env.get_environment()
        log_level = env.get_log_level()
        debug_mode = env.get_config_value(current_env, "DEBUG", False)
        
        logger.info(f"実行環境: {current_env}, ログレベル: {log_level}, デバッグモード: {debug_mode}")
        return True
        
    except Exception as e:
        logger.error(f"環境の初期化に失敗しました: {e}")
        return False

def initialize_browser(headless: bool = False) -> Browser:
    """ブラウザを初期化します"""
    try:
        # タイムアウト値の取得
        timeout = int(env.get_config_value('BROWSER', 'timeout', '10'))
        
        # ブラウザインスタンスの作成と初期化
        browser = Browser(
            logger=logger,
            headless=headless,
            timeout=timeout
        )
        
        if not browser.setup():
            raise Exception("ブラウザのセットアップに失敗しました")
            
        logger.info("ブラウザを初期化しました")
        return browser
        
    except Exception as e:
        logger.error(f"ブラウザの初期化に失敗しました: {e}")
        raise

def main():
    """メイン処理を実行します"""
    try:
        # 環境の初期化
        if not initialize_environment():
            return 1
            
        # コマンドライン引数の解析
        args = parse_args()
        
        # ダウンロードディレクトリの作成
        download_dir = os.path.abspath(args.download_dir)
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"ダウンロードディレクトリを作成しました: {download_dir}")
        
        # ブラウザの初期化
        browser = initialize_browser(args.headless)
        
        try:
            # ログインページの初期化と実行
            login_page = EbisLoginPage(browser, logger)
            logger.info("ログイン処理を開始します")
            
            # ログインページに移動してログイン実行
            login_page.navigate_to_login_page()
            if not login_page.login():
                logger.error("ログインに失敗しました")
                return 1
                
            # CSVダウンローダーの初期化と実行
            downloader = EbisCSVDownloader(
                browser=browser,
                logger=logger,
                download_dir=download_dir
            )
            
            # 実行するレポートタイプを決定
            report_types = []
            if args.type == "all":
                report_types = ["detailed_analysis", "cv_attribute"]
            else:
                report_types = [args.type]
                
            download_results = {}
            
            # 各レポートタイプのダウンロードを実行
            for report_type in report_types:
                logger.info(f"{report_type}のダウンロードを開始します")
                
                try:
                    if report_type == "detailed_analysis":
                        # 詳細分析レポートのダウンロード
                        csv_file = downloader.download_csv(
                            csv_type=report_type,
                            start_date=args.start,
                            end_date=args.end
                        )
                    elif report_type == "cv_attribute":
                        # コンバージョン属性レポートのダウンロード
                        csv_file = downloader.download_cv_attribute_csv(
                            start_date=args.start,
                            end_date=args.end
                        )
                    
                    if csv_file:
                        logger.info(f"{report_type}のダウンロードが完了しました: {csv_file}")
                        download_results[report_type] = csv_file
                    else:
                        logger.error(f"{report_type}のダウンロードに失敗しました")
                        download_results[report_type] = None
                        
                        # ダウンロードディレクトリの状態を確認
                        if os.path.exists(download_dir):
                            try:
                                files = os.listdir(download_dir)
                                logger.debug(f"ダウンロードディレクトリの内容: {files}")
                            except Exception as e:
                                logger.error(f"ダウンロードディレクトリの確認中にエラー: {e}")
                        
                        # ブラウザの状態を確認
                        try:
                            current_url = browser.get_current_url()
                            logger.debug(f"現在のURL: {current_url}")
                            browser.save_screenshot(f"{report_type}_download_failed_state")
                            logger.info(f"スクリーンショットを保存しました: {report_type}_download_failed_state")
                        except Exception as e:
                            logger.error(f"ブラウザ状態の確認中にエラー: {e}")
                        
                except CSVDownloadError as e:
                    logger.error(f"{report_type}ダウンロード中にエラーが発生: {e}")
                    browser.save_screenshot(f"{report_type}_download_error_detail")
                    logger.info(f"エラー時のスクリーンショットを保存しました: {report_type}_download_error_detail")
                    download_results[report_type] = None
            
            # 結果のサマリーを表示
            logger.info("ダウンロード結果サマリー:")
            success_count = sum(1 for result in download_results.values() if result)
            for report_type, file_path in download_results.items():
                status = "成功" if file_path else "失敗"
                logger.info(f"  {report_type}: {status} {file_path if file_path else ''}")
            
            # すべてのレポートタイプでダウンロードが失敗した場合は失敗として終了
            if success_count == 0:
                logger.error("すべてのレポートダウンロードが失敗しました")
                return 1
            
            # 一部でも成功していれば成功として終了
            return 0
                
        finally:
            # ブラウザの終了
            browser.quit()
            logger.info("ブラウザを終了しました")
            
    except LoginError as e:
        logger.error(f"ログインエラー: {e}")
        return 1
    except CSVDownloadError as e:
        logger.error(f"CSVダウンロードエラー: {e}")
        return 1
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
