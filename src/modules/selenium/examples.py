#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汎用モジュールの使用例

このファイルには、汎用Browserクラスとその関連モジュールの使用方法を示すサンプルコードが含まれています。
実際の使用シーンに応じて適宜カスタマイズしてください。
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
import traceback
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By

# 相対パスの設定
current_dir = os.path.dirname(os.path.abspath(__file__))
# 親ディレクトリ（src/modules）
parent_dir = os.path.dirname(current_dir)
# プロジェクトルート
root_dir = os.path.dirname(parent_dir)

# パスを追加
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if parent_dir not in sys.path:
    sys.path.append(parent_dir)

if root_dir not in sys.path:
    sys.path.append(root_dir)

# 汎用モジュールのインポート
try:
    # プロジェクトルートからの実行用 - src.modules.generic から src.modules.selenium に修正
    from src.modules.selenium.browser import Browser
    from src.modules.selenium.login_page import LoginPage
except (ModuleNotFoundError, ImportError):
    try:
        # 相対インポートを試行
        from .browser import Browser
        from .login_page import LoginPage
    except (ImportError, ValueError):
        # 直接実行用インポート
        from browser import Browser
        from login_page import LoginPage


def setup_logger(log_level=logging.INFO):
    """
    ブラウザの例で使用するロガーをセットアップする
    
    Args:
        log_level (int): ログレベル
    
    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    logger = logging.getLogger("browser_example")
    
    if not logger.handlers:
        # ハンドラーの設定
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)
    
    return logger


def simple_example():
    """
    汎用Browserクラスの基本的な使い方の例
    
    このサンプルでは：
    1. ロガーをセットアップ
    2. Browserインスタンスを作成
    3. Googleにアクセス
    4. 検索を実行
    5. スクリーンショットを取得
    """
    logger = setup_logger()
    logger.info("=== 基本的なブラウザ使用例を開始します ===")
    
    try:
        # Browserインスタンスの作成
        browser = Browser(headless=False, logger=logger)
        if not browser.setup():
            logger.error("ブラウザのセットアップに失敗しました")
            return
        
        # Googleにアクセス
        if not browser.navigate_to("https://www.google.com"):
            logger.error("Googleへのアクセスに失敗しました")
            browser.quit()
            return
        
        # 検索ボックスを見つけて検索を実行
        search_box = browser.wait_for_element((By.NAME, "q"))
        if search_box:
            search_box.clear()
            search_box.send_keys("Selenium Python automation")
            search_box.submit()
            
            # 結果が表示されるのを待つ
            time.sleep(2)
            
            # スクリーンショットを取得
            browser.save_screenshot("google_search_results.png")
            logger.info("検索結果のスクリーンショットを保存しました: google_search_results.png")
            
            # 検索結果を取得
            search_results = browser.find_elements(By.CSS_SELECTOR, "div.g")
            logger.info(f"検索結果数: {len(search_results) if search_results else 0}")
            
            # 最初の検索結果のタイトルを取得
            if search_results and len(search_results) > 0:
                first_result_title = browser.wait_for_element((By.CSS_SELECTOR, "div.g h3"))
                if first_result_title:
                    logger.info(f"最初の検索結果: {first_result_title.text}")
        else:
            logger.error("検索ボックスが見つかりませんでした")
        
        # ブラウザを閉じる
        browser.quit()
        logger.info("=== 基本的なブラウザ使用例を終了します ===")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        logger.debug(traceback.format_exc())


def selector_example():
    """
    セレクタファイルを使用したブラウザ操作の例
    
    このサンプルでは：
    1. ロガーをセットアップ
    2. セレクタファイルを指定してBrowserインスタンスを作成
    3. Webサイトにアクセス
    4. セレクタファイルで定義された要素を操作
    """
    logger = setup_logger()
    logger.info("=== セレクタファイルを使用したブラウザ使用例を開始します ===")
    
    # カレントディレクトリの取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # セレクタファイルのパス
    selectors_path = os.path.join(current_dir, "selectors_example.csv")
    
    # セレクタファイルが存在しない場合は作成
    if not os.path.exists(selectors_path):
        with open(selectors_path, "w", encoding="utf-8") as f:
            f.write("グループ,名前,セレクタ種別,セレクタ値,説明\n")
            f.write("google,search_box,name,q,検索ボックス\n")
            f.write("google,search_results,css,div.g,検索結果リスト\n")
            f.write("google,first_result,css,div.g h3,最初の検索結果タイトル\n")
        logger.info(f"サンプルセレクタファイルを作成しました: {selectors_path}")
    
    try:
        # Browserインスタンスの作成（セレクタファイルを指定）
        browser = Browser(
            selectors_path=selectors_path, 
            headless=False, 
            logger=logger
        )
        
        if not browser.setup():
            logger.error("ブラウザのセットアップに失敗しました")
            return
        
        # Googleにアクセス
        if not browser.navigate_to("https://www.google.com"):
            logger.error("Googleへのアクセスに失敗しました")
            browser.quit()
            return
        
        # セレクタファイルで定義された要素を使用
        search_box = browser.get_element("google", "search_box")
        if search_box:
            search_box.clear()
            search_box.send_keys("Selenium automation with Python")
            search_box.submit()
            
            # 結果が表示されるのを待つ
            time.sleep(2)
            
            # スクリーンショットを取得
            browser.save_screenshot("google_search_selector_example.png")
            logger.info("検索結果のスクリーンショットを保存しました: google_search_selector_example.png")
            
            # セレクタファイルを使用して検索結果を取得
            search_results = browser.get_elements("google", "search_results")
            logger.info(f"検索結果数: {len(search_results) if search_results else 0}")
            
            # 最初の検索結果のタイトルを取得
            first_result_title = browser.get_element("google", "first_result")
            if first_result_title:
                logger.info(f"最初の検索結果: {first_result_title.text}")
        else:
            logger.error("検索ボックスが見つかりませんでした")
        
        # ブラウザを閉じる
        browser.quit()
        logger.info("=== セレクタファイルを使用したブラウザ使用例を終了します ===")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        logger.debug(traceback.format_exc())


def login_example():
    """
    LoginPageクラスを使用したログイン処理の例
    
    このサンプルでは：
    1. ロガーをセットアップ
    2. 設定を定義
    3. LoginPageインスタンスを作成
    4. ログイン処理を実行
    """
    logger = setup_logger()
    logger.info("=== LoginPageクラスを使用したログイン例を開始します ===")
    
    # カレントディレクトリの取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # セレクタファイルのパス
    selectors_path = os.path.join(current_dir, "login_selectors_example.csv")
    
    # セレクタファイルが存在しない場合は作成
    if not os.path.exists(selectors_path):
        with open(selectors_path, "w", encoding="utf-8") as f:
            f.write("グループ,名前,セレクタ種別,セレクタ値,説明\n")
            f.write("login,username,id,username,ユーザー名入力欄\n")
            f.write("login,password,id,password,パスワード入力欄\n")
            f.write("login,login_button,css,button[type='submit'],ログインボタン\n")
        logger.info(f"サンプルログインセレクタファイルを作成しました: {selectors_path}")
    
    try:
        # ログイン設定
        config = {
            'browser': {
                'headless': 'false'
            },
            'login': {
                'url': 'https://example.com/login',
                'username': 'test_user',
                'password': 'test_password'
            }
        }
        
        # LoginPageインスタンスを作成
        login_page = LoginPage(
            config=config,
            selectors_path=selectors_path,
            logger=logger
        )
        
        # ログイン処理を実行
        logger.info("ログイン処理を実行します")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        logger.debug(traceback.format_exc())


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ブラウザ自動化の例")
    parser.add_argument(
        "--example", 
        choices=["simple", "selector", "login", "all"], 
        default="all",
        help="実行する例を選択します"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="デバッグモードを有効にします"
    )
    
    args = parser.parse_args()
    
    # ログレベルの設定
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # 選択された例を実行
    if args.example == "simple" or args.example == "all":
        simple_example()
    
    if args.example == "selector" or args.example == "all":
        selector_example()
    
    if args.example == "login" or args.example == "all":
        login_example()


if __name__ == "__main__":
    main() 