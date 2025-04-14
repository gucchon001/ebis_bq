#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ad Ebis 詳細分析ページからCSVをダウンロードするモジュール

このモジュールは、Ad Ebisの詳細分析ページにアクセスし、
指定した条件でCSVファイルをダウンロードする機能を提供します。

主な機能:
- 詳細分析ページへのナビゲーション
- 分析期間や条件の設定
- CSVダウンロードボタンの操作
- ダウンロード完了の検出と確認

依存モジュール:
- src.modules.selenium.browser: ブラウザ操作の基本機能を提供
- src.utils.environment: 環境変数や設定ファイルからの値取得
"""

import logging
import os
import time
import csv
import json
import shutil
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import glob
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 基本モジュールのインポート
from src.modules.selenium.browser import Browser
from src.modules.selenium.page_analyzer import PageAnalyzer

# 環境変数/設定ファイル操作のためのユーティリティをインポート
from src.utils.environment import env
from src.utils.logging_config import get_logger

logger = logging.getLogger(__name__)

class CSVDownloadError(Exception):
    """CSVダウンロード処理中のエラーを表す例外クラス"""
    pass

class EbisCSVDownloader:
    """
    Ad Ebisの詳細分析ページからCSVをダウンロードするクラス
    
    このクラスは、詳細分析ページにアクセスして
    各種レポートのCSVデータをダウンロードする機能を提供します。
    
    Attributes:
        browser (Browser): ブラウザ操作を行うインスタンス
        logger (logging.Logger): ログ出力用ロガー
        page_analyzer (PageAnalyzer): ページ要素解析用インスタンス
        selector_group (str): 使用するセレクタのグループ名
        download_dir (str): ダウンロードファイルの保存先ディレクトリ
    """
    
    def __init__(
        self,
        browser: Browser,
        logger: Optional[logging.Logger] = None,
        download_dir: str = "data/downloads",
        config: Optional[Dict[str, Any]] = None,
        page_load_wait: int = 1,
        element_timeout: int = 10,
        analysis_url: Optional[str] = None
    ):
        """
        Args:
            browser: 初期化済みのブラウザインスタンス
            logger: カスタムロガー（指定されていない場合は新規作成）
            download_dir: ダウンロードディレクトリのパス
            config: 設定辞書（指定された場合はこれを優先使用）
            page_load_wait: ページ読み込み後の待機時間（秒）
            element_timeout: 要素の待機タイムアウト（秒）
            analysis_url: 詳細分析ページのURL（省略可能）
        """
        # ロガーの設定
        self.logger = logger or get_logger(__name__)
        
        # 設定の初期化
        self.config = config or {}
        
        # ダウンロードディレクトリを設定（パスを正規化）
        # 相対パスの場合は絶対パスに変換
        if not os.path.isabs(download_dir):
            # 現在の作業ディレクトリからの相対パス
            download_dir = os.path.abspath(download_dir)
            
        self.download_dir = os.path.normpath(download_dir)
        self.logger.info(f"ダウンロードディレクトリを設定しました: {self.download_dir}")
        
        # ダウンロードディレクトリが存在しない場合は作成
        if not os.path.exists(self.download_dir):
            try:
                os.makedirs(self.download_dir, exist_ok=True)
                self.logger.info(f"ダウンロードディレクトリを作成しました: {self.download_dir}")
            except Exception as e:
                self.logger.warning(f"ダウンロードディレクトリの作成中にエラーが発生しました: {str(e)}")
        
        self.page_load_wait = page_load_wait
        self.element_timeout = element_timeout
        
        # 詳細分析ページのURLを設定
        self.analysis_url = analysis_url or env.get_config_value('CSV_DOWNLOAD', 'analysis_url')
        if not self.analysis_url:
            self.logger.warning("詳細分析ページのURLが設定されていません")
        
        # コンバージョン属性ページのURLを設定
        self.cv_attribute_url = env.get_config_value('CSV_DOWNLOAD', 'cv_attribute_url')
        if not self.cv_attribute_url:
            self.logger.warning("コンバージョン属性ページのURLが設定されていません")
        
        # セレクタグループの設定
        self.selector_group = "detailed_analysis"
        # 共通セレクタグループの設定
        self.common_selector_group = "common"
        
        # ブラウザインスタンスを設定
        self.browser = browser
        self.logger.info("ブラウザインスタンスを設定しました")
        
        # ページ解析用インスタンスの作成
        self.page_analyzer = PageAnalyzer(self.browser, self.logger)
        
        # 設定からタイムアウト値などを取得
        # download_timeoutは実際にはdownload_waitとして設定ファイルに記載されている
        download_wait = env.get_config_value('CSV_DOWNLOAD', 'download_wait', '60')
        # タイムアウト値を整数に変換し、最低30秒を確保
        self.download_timeout = max(int(download_wait), 30)
        
    def __enter__(self):
        """コンテキストマネージャーのエントリポイント"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        pass
            
    def navigate_to_analysis_page(self) -> bool:
        """
        詳細分析ページに移動します
        
        Returns:
            bool: 移動が成功した場合はTrue、失敗した場合はFalse
            
        Raises:
            CSVDownloadError: 詳細分析ページへの移動に失敗した場合
        """
        try:
            # 詳細分析ページのURLに直接アクセス
            analysis_url = self.analysis_url
            if not analysis_url:
                error_msg = "詳細分析ページのURLが設定されていません"
                self.logger.error(error_msg)
                raise CSVDownloadError(error_msg)
            
            self.logger.info(f"詳細分析ページに直接アクセスします: {analysis_url}")
            self.browser.navigate_to(analysis_url)
            
            # ページ読み込み待機
            self.logger.debug(f"ページ読み込みの待機中... ({self.page_load_wait}秒)")
            time.sleep(self.page_load_wait)
            
            # 全トラフィックタブの表示を確認（簡素化した実装）
            self.logger.info("全トラフィックタブの表示を確認します")
            if not self.browser.get_element(self.common_selector_group, "all_traffic_tab", wait_time=self.element_timeout):
                error_msg = "全トラフィックタブが見つかりません"
                self.logger.error(error_msg)
                self.browser.save_screenshot("error_analysis_page_tab_not_found")
                raise CSVDownloadError(error_msg)
            
            self.logger.info("詳細分析ページの表示を確認しました")
            return True
                
        except Exception as e:
            error_msg = f"詳細分析ページへの移動中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("error_analysis_page")
            raise CSVDownloadError(error_msg)
            
    def _navigate_to_cv_attribute_page(self):
        """コンバージョン属性レポートページに移動します"""
        try:
            self.logger.info("コンバージョン属性レポートページに移動します")
            
            # 設定ファイルからコンバージョン属性ページのURLを取得
            cv_attribute_url = None
            
            # configが辞書型の場合
            if isinstance(self.config, dict):
                # 辞書からCSV_DOWNLOADセクションを取得
                csv_download_section = self.config.get('CSV_DOWNLOAD', {})
                if isinstance(csv_download_section, dict):
                    # セクションからcv_attribute_urlを取得
                    cv_attribute_url = csv_download_section.get('cv_attribute_url')
            # configがConfigParserオブジェクトの場合
            else:
                try:
                    cv_attribute_url = self.config.get('CSV_DOWNLOAD', 'cv_attribute_url')
                except:
                    # ConfigParserとしての取得に失敗した場合は何もしない
                    pass
                    
            # 上記のいずれからも取得できなかった場合は、インスタンス変数またはenvから取得
            if not cv_attribute_url:
                cv_attribute_url = self.cv_attribute_url or env.get_config_value('CSV_DOWNLOAD', 'cv_attribute_url', None)
            
            if not cv_attribute_url:
                # URLが設定されていない場合はエラー
                error_msg = "コンバージョン属性ページのURLが設定ファイルに定義されていません"
                self.logger.error(error_msg)
                raise CSVDownloadError(error_msg)
            
            # URL先に移動
            self.browser.navigate_to(cv_attribute_url)
            self.logger.info(f"コンバージョン属性ページ({cv_attribute_url})に移動しました")
            
            # ページの読み込み完了を待機
            self.browser.wait_for_page_load(timeout=self.element_timeout)
            
            # ページのコンテンツが読み込まれるまで適切に待機
            self.logger.info("コンバージョン属性ページのコンテンツ読み込みを待機しています...")
            
            # JavaScript DOMが完全に読み込まれるのを待機
            try:
                from selenium.webdriver.common.by import By
                # テーブル要素や主要コンテンツの読み込みを待機
                if self.browser.wait_for_element(By.CSS_SELECTOR, "table, .data-table, [role='grid'], .main-content", timeout=10):
                    self.logger.info("メインコンテンツの読み込みが確認できました")
                else:
                    self.logger.warning("メインコンテンツの読み込みが確認できませんでしたが、処理を続行します")
            except Exception as wait_error:
                self.logger.warning(f"コンテンツ待機中に例外が発生しましたが、処理を続行します: {wait_error}")
            
            # 安全のため5秒の固定待機を追加
            self.logger.info("ページの安定化のため5秒間待機します")
            time.sleep(5)
            
            # ページのスクリーンショットを取得
            self.browser.save_screenshot("cv_attribute_page_loaded")
            
        except Exception as e:
            error_msg = f"コンバージョン属性レポートページへの移動中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("cv_attribute_navigation_error")
            raise CSVDownloadError(error_msg) from e
            
    def set_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        click_container: bool = True
    ) -> bool:
        """
        詳細分析ページの日付範囲を設定します
        
        Args:
            start_date (Optional[str]): 開始日（YYYY-MM-DD形式）。Noneの場合は30日前を使用
            end_date (Optional[str]): 終了日（YYYY-MM-DD形式）。Noneの場合は今日を使用
            click_container (bool): 日付選択コンテナをクリックするかどうか。デフォルトはTrue
            
        Returns:
            bool: 日付範囲の設定に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 日付パラメータが文字列の場合はdatetimeオブジェクトに変換
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).date()
                self.logger.debug(f"開始日が指定されていないため、30日前({start_date})をデフォルトとして使用します")
            elif isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                
            if end_date is None:
                end_date = datetime.now().date()
                self.logger.debug(f"終了日が指定されていないため、当日({end_date})をデフォルトとして使用します")
            elif isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # 日付が変わっているか確認するために、ピッカーの表示前の現在の値を取得
            try:
                current_start = self.browser.get_element(
                    self.selector_group, "datetime_range_start", wait_time=self.element_timeout
                )
                current_end = self.browser.get_element(
                    self.selector_group, "datetime_range_end", wait_time=self.element_timeout
                )
                self.logger.debug(f"現在の日付範囲: {current_start.get_attribute('value')} - {current_end.get_attribute('value')}")
            except Exception as e:
                self.logger.warning(f"現在の日付範囲を取得できませんでした: {e}")

            # 日付ピッカーコンテナを表示する必要がある場合のみクリック
            if click_container:
                # 日付ピッカーのトリガーをクリック
                if not self.browser.click_element_by_selector(
                    self.selector_group, "datetime_picker_trigger", timeout=self.element_timeout
                ):
                    self.logger.error("日付ピッカーのトリガーが見つかりませんでした")
                    self.browser.save_screenshot("datetime_picker_trigger_not_found")
                    return False

                # 日付ピッカーコンテナが表示されるのを待つ
                if not self.browser.wait_for_element(
                    self.selector_group, "datetime_picker_container", wait_time=self.element_timeout
                ):
                    self.logger.error("日付ピッカーコンテナが見つかりませんでした")
                    self.browser.save_screenshot("datetime_picker_container_not_found")
                    return False

            # 入力フィールドにアクセス
            start_input = self.browser.get_element(
                self.selector_group, "datetime_range_start", wait_time=self.element_timeout
            )
            if not start_input:
                self.logger.error("開始日入力フィールドが見つかりませんでした")
                self.browser.save_screenshot("start_date_input_not_found")
                return False

            end_input = self.browser.get_element(
                self.selector_group, "datetime_range_end", wait_time=self.element_timeout
            )
            if not end_input:
                self.logger.error("終了日入力フィールドが見つかりませんでした")
                self.browser.save_screenshot("end_date_input_not_found")
                return False

            # 日付ピッカーの表示が確認できた場合は、日付を入力
            if click_container:
                # 日付ピッカーの表示が確認できた場合は、日付を入力
                date_format = "%Y-%m-%d"
                formatted_date_range = f"{start_date.strftime(date_format)} - {end_date.strftime(date_format)}"
                
                # 日付入力フィールドを見つける - 修正部分
                if not self.browser.input_text_by_selector(
                    self.selector_group, "datetime_range_start", formatted_date_range, clear_first=True, timeout=self.element_timeout
                ):
                    error_msg = "日付入力フィールドが見つかりませんでした"
                    self.logger.error(error_msg)
                    self.browser.save_screenshot("date_input_field_not_found")
                    return False
                
                # 適用ボタンをクリック
                if not self.browser.click_element_by_selector(self.selector_group, "apply_button", timeout=self.element_timeout):
                    error_msg = "日付適用ボタンが見つかりませんでした"
                    self.logger.error(error_msg)
                    self.browser.save_screenshot("apply_button_not_found")
                    return False
                
                # 変更が反映されるまで待機
                self.logger.debug(f"日付変更の反映を待機しています... ({self.page_load_wait}秒)")
                time.sleep(self.page_load_wait)
                
                self.logger.info(f"日付範囲の設定が完了しました: {start_date} ～ {end_date}")
            else:
                self.logger.info("日付選択コンテナのクリックはスキップします（デフォルト値を使用）")
            
            return True
            
        except Exception as e:
            error_msg = f"日付範囲の設定中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("set_date_range_error")
            return False
            
    def _export_and_download_csv(self, file_pattern, output_path=None):
        """
        エクスポートボタンを押して表をCSVでダウンロードする共通処理

        Args:
            file_pattern (str): ダウンロードするCSVファイルのパターン（例: 'detail_analyze', 'cv_attr'）
            output_path (str, optional): 出力先パス

        Returns:
            str: ダウンロードしたCSVファイルのパス

        Raises:
            CSVDownloadError: CSVダウンロード中にエラーが発生した場合
        """
        try:
            # エクスポートボタンをクリック - 待機時間を明示的に設定
            self.logger.info("エクスポートボタンをクリックします")
            if not self.browser.click_element_by_selector("common", "export_button", wait_time=5, timeout=self.element_timeout):
                error_msg = "エクスポートボタンが見つかりませんでした"
                self.logger.error(error_msg)
                self.browser.save_screenshot("export_button_not_found")
                raise CSVDownloadError(error_msg)
                
            # ドロップダウンメニューが表示されるのを待機
            self.logger.info("ドロップダウンメニューの表示を待機しています")
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support import expected_conditions as EC
                
                # ドロップダウンメニューがCSSクラス .dropdown-menu.show または同様の識別子を持つ場合
                dropdown_visible = self.browser.wait_for_element(
                    By.CSS_SELECTOR, 
                    ".dropdown-menu.show, .dropdown-menu, [role='menu'], [aria-expanded='true']", 
                    timeout=5
                )
                
                if dropdown_visible:
                    self.logger.info("ドロップダウンメニューが表示されました")
                else:
                    self.logger.warning("ドロップダウンメニューの表示が確認できませんでしたが、処理を継続します")
            except Exception as e:
                self.logger.warning(f"ドロップダウンメニュー待機中に例外が発生しましたが、処理を続行します: {e}")
            
            # 表を出力（CSV）をクリック - JavaScriptクリックも試み、待機時間を明示的に設定
            self.logger.info("表を出力（CSV）ボタンをクリックします")
            try:
                if not self.browser.click_element_by_selector("common", "csv_download_button", wait_time=5, timeout=self.element_timeout):
                    self.logger.warning("表を出力（CSV）ボタンが見つかりませんでした。JavaScriptを使って試みます。")
                    
                    # JavaScriptを使ったクリックを試みる
                    if not self.browser.click_element_by_selector("common", "csv_download_button", use_js=True, wait_time=3, timeout=self.element_timeout):
                        error_msg = "表を出力（CSV）ボタンが見つかりませんでした"
                        self.logger.error(error_msg)
                        self.browser.save_screenshot("csv_download_button_not_found")
                        raise CSVDownloadError(error_msg)
                    else:
                        self.logger.info("JavaScriptを使用して表を出力（CSV）ボタンをクリックしました")
                else:
                    self.logger.info("表を出力（CSV）ボタンをクリックしました")
            except Exception as e:
                error_msg = f"表を出力（CSV）ボタンのクリック中にエラーが発生しました: {e}"
                self.logger.error(error_msg)
                self.browser.save_screenshot("csv_download_error")
                raise CSVDownloadError(error_msg)
            
            # ダウンロードの完了を待機
            self.logger.debug(f"ダウンロードの完了を待機しています... ({self.download_timeout}秒)")
            
            # ユーザーのデフォルトダウンロードディレクトリを取得
            default_download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(default_download_dir):
                self.logger.warning(f"デフォルトダウンロードディレクトリが存在しません: {default_download_dir}")
                raise CSVDownloadError(f"デフォルトダウンロードディレクトリが見つかりません: {default_download_dir}")
            
            # ダウンロード開始前に5秒待機
            self.logger.info("ダウンロード開始を待機しています（5秒）...")
            time.sleep(5)
            
            # ダウンロード前のファイルリストを取得（比較用）
            pre_download_files = set()
            
            try:
                pre_download_files = set([f for f in os.listdir(default_download_dir) 
                                      if os.path.isfile(os.path.join(default_download_dir, f)) and 
                                      f.lower().endswith('.csv')])
                self.logger.debug(f"デフォルトダウンロードディレクトリのCSVファイル数: {len(pre_download_files)}")
            except Exception as e:
                self.logger.warning(f"ダウンロード前のファイル一覧取得中にエラー: {e}")
            
            # ダウンロードファイルをポーリングで確認
            start_time = time.time()
            found_file = None
            last_log_time = start_time  # 頻繁なログ出力を防ぐ
            
            self.logger.info(f"デフォルトダウンロードディレクトリを監視しています: {default_download_dir}")
            
            while time.time() - start_time < self.download_timeout:
                try:
                    # 現在のファイルリストを取得
                    current_files = set([f for f in os.listdir(default_download_dir) 
                                      if os.path.isfile(os.path.join(default_download_dir, f)) and 
                                      f.lower().endswith('.csv')])
                    
                    # ダウンロード前に存在しなかった新しいファイルを探す
                    new_files = current_files - pre_download_files
                    
                    # 新しいファイルが見つかった場合、パターンでフィルタリング
                    if new_files:
                        # ファイル名にパターンを含むファイルをフィルタリング
                        matching_files = [f for f in new_files if file_pattern.lower() in f.lower()]
                        
                        if matching_files:
                            # 最新のファイルを取得（作成日時でソート）
                            found_file = max(matching_files, key=lambda f: os.path.getctime(os.path.join(default_download_dir, f)))
                            found_file = os.path.join(default_download_dir, found_file)
                            self.logger.info(f"ダウンロードファイルを検出しました: {found_file}")
                            break
                        else:
                            # パターンに一致するファイルがない場合でも、他の新しいCSVファイルを候補として記録
                            self.logger.debug(f"新しいCSVファイルを検出しましたが、パターン'{file_pattern}'に一致しません。待機を継続します。")
                except Exception as e:
                    self.logger.warning(f"ファイル監視中にエラー: {e}")
                
                # 一定時間ごとにログを出力
                current_time = time.time()
                if current_time - last_log_time > 5:
                    elapsed = current_time - start_time
                    remaining = self.download_timeout - elapsed
                    self.logger.debug(f"ダウンロード待機中... 経過: {elapsed:.1f}秒, 残り: {remaining:.1f}秒")
                    last_log_time = current_time
                
                time.sleep(1)
            
            # ファイルが見つからない場合
            if not found_file:
                # ポーリングを延長して監視を継続する
                self.logger.warning(f"パターン'{file_pattern}'に一致するファイルが見つかりませんでした。ポーリングを延長します...")
                
                # 追加の監視時間 - 最低60秒、最大120秒の延長
                extended_timeout = max(min(120, self.download_timeout * 2), 60)
                extended_start_time = time.time()
                
                self.logger.info(f"ポーリングを{extended_timeout}秒間延長します")
                
                # 現在のファイルリストを取得（比較用）
                try:
                    current_files = set([f for f in os.listdir(default_download_dir) 
                                      if os.path.isfile(os.path.join(default_download_dir, f)) and f.lower().endswith('.csv')])
                except Exception as e:
                    self.logger.warning(f"ファイル一覧取得中にエラー: {e}")
                    current_files = set()
                
                # 延長したポーリングでファイルを監視
                while time.time() - extended_start_time < extended_timeout:
                    try:
                        # 現在のファイルリストを取得
                        new_current_files = set([f for f in os.listdir(default_download_dir) 
                                              if os.path.isfile(os.path.join(default_download_dir, f)) and f.lower().endswith('.csv')])
                        
                        # 監視開始後に追加されたファイルを探す
                        new_files = new_current_files - current_files
                        
                        # 新しいファイルが見つかった場合、パターンでフィルタリング
                        if new_files:
                            # ファイル名にパターンを含むファイルをフィルタリング
                            matching_files = [f for f in new_files if file_pattern.lower() in f.lower()]
                            
                            if matching_files:
                                # 最新のファイルを取得（作成日時でソート）
                                found_file = max(matching_files, key=lambda f: os.path.getctime(os.path.join(default_download_dir, f)))
                                found_file = os.path.join(default_download_dir, found_file)
                                self.logger.info(f"延長ポーリングで一致するファイルを検出しました: {found_file}")
                                break
                            else:
                                self.logger.debug(f"新しいCSVファイルを検出しましたが、パターン'{file_pattern}'に一致しません。監視を継続します。")
                    except Exception as e:
                        self.logger.warning(f"延長ポーリング中にエラー: {e}")
                    
                    # 一定間隔で待機
                    time.sleep(1)
                
                # 延長ポーリングでもファイルが見つからなかった場合
                if not found_file:
                    error_msg = f"パターン '{file_pattern}' に一致するファイルが見つかりませんでした。"
                    self.logger.error(error_msg)
                    self.browser.save_screenshot("csv_download_not_found")
                    raise CSVDownloadError(error_msg)
            
            # 現在の日付を取得して標準ファイル名を生成
            today = datetime.now().strftime('%Y%m%d')
            
            # 出力パスが指定されている場合はそれを使用、そうでなければデフォルトの命名規則を適用
            if output_path:
                target_file = output_path
            else:
                # プログラム指定のダウンロードディレクトリが存在しない場合は作成
                if not os.path.exists(self.download_dir):
                    os.makedirs(self.download_dir, exist_ok=True)
                    self.logger.info(f"ダウンロードディレクトリを作成しました: {self.download_dir}")
                
                # ファイル名の生成
                if file_pattern == 'detail_analyze':
                    target_file = os.path.join(self.download_dir, f"{today}_ebis_detailed_report.csv")
                elif file_pattern == 'cv_attr':
                    target_file = os.path.join(self.download_dir, f"{today}_ebis_conversion_attribute.csv")
                else:
                    target_file = os.path.join(self.download_dir, f"{today}_ebis_{file_pattern}_report.csv")
            
            # 出力ディレクトリが存在しない場合は作成
            output_dir = os.path.dirname(target_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                self.logger.info(f"出力ディレクトリを作成しました: {output_dir}")
            
            # ファイルが既に存在する場合はバックアップ
            if os.path.exists(target_file):
                backup_file = f"{target_file}.bak"
                try:
                    shutil.copy2(target_file, backup_file)
                    self.logger.info(f"既存ファイルをバックアップしました: {backup_file}")
                except Exception as e:
                    self.logger.warning(f"バックアップ作成中にエラーが発生しました: {e}")
            
            # デフォルトダウンロードディレクトリからプログラム指定のディレクトリにファイルを移動
            try:
                self.logger.info(f"ファイルを移動します: {found_file} -> {target_file}")
                shutil.move(found_file, target_file)
                self.logger.info(f"ダウンロードしたファイルを移動しました: {target_file}")
                
                return target_file
            except Exception as e:
                self.logger.error(f"ファイル移動中にエラーが発生しました: {e}")
                
                # ファイルをコピーして元のファイルを残す方法を試す
                try:
                    self.logger.info(f"ファイルをコピーします: {found_file} -> {target_file}")
                    shutil.copy2(found_file, target_file)
                    self.logger.info(f"ファイルをコピーしました: {target_file}")
                    
                    return target_file
                except Exception as copy_error:
                    self.logger.error(f"ファイルコピー中にエラーが発生しました: {copy_error}")
                    # 元のファイルパスを返す
                    return found_file
        
        except Exception as e:
            error_msg = f"CSVダウンロード中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("download_csv_error")
            raise CSVDownloadError(error_msg)

    def download_csv(
        self,
        csv_type: str,
        output_path: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        traffic_type: str = "all",
        use_yesterday: bool = True  # デフォルトで「昨日」を使用するように変更
    ) -> str:
        """
        詳細分析画面からCSVをダウンロードします。

        Args:
            csv_type (str): ダウンロードするCSVの種類 ("detailed_analysis" のみサポート)
            output_path (Optional[str], optional): 出力先パス. Defaults to None.
            start_date (Optional[str], optional): 開始日 (YYYY-MM-DD形式). Defaults to None.
            end_date (Optional[str], optional): 終了日 (YYYY-MM-DD形式). Defaults to None.
            traffic_type (str, optional): トラフィックタイプ. Defaults to "all".
            use_yesterday (bool, optional): 「昨日」の日付を使用するかどうか. Defaults to True.

        Returns:
            str: ダウンロードしたCSVファイルのパス

        Raises:
            CSVDownloadError: CSVダウンロード中にエラーが発生した場合
        """
        try:
            self.logger.info(f"{csv_type} CSVのダウンロードを開始します")
            
            # 分析ページに移動
            self.navigate_to_analysis_page()
            
            # 「昨日」の設定を優先
            if use_yesterday:
                self.logger.info("「昨日」の日付を使用します")
                # 日付ピッカーのトリガーをクリック
                if not self.browser.click_element_by_selector(
                    self.common_selector_group, "date_picker_trigger", timeout=self.element_timeout
                ):
                    self.logger.error("日付ピッカーのトリガーが見つかりませんでした")
                    self.browser.save_screenshot("date_picker_trigger_not_found")
                    # エラーだが処理を続行
                else:
                    # 日付ピッカーが表示されるまで待機
                    self.logger.info("日付ピッカーの表示を待機しています...")
                    time.sleep(2)
                    
                    # 「昨日」を選択
                    self.logger.info("「昨日」を選択します")
                    if not self.browser.click_element_by_selector(
                        self.common_selector_group, "yesterday_date_input", timeout=self.element_timeout
                    ):
                        self.logger.error("「昨日」の選択肢が見つかりませんでした")
                        self.browser.save_screenshot("yesterday_option_not_found")
                        # エラーが発生した場合、通常の日付設定に切り替え
                    else:
                        # 「適用」ボタンをクリック
                        self.logger.info("適用ボタンをクリックします")
                        if not self.browser.click_element_by_selector(
                            self.common_selector_group, "apply_button", timeout=self.element_timeout
                        ):
                            self.logger.error("適用ボタンが見つかりませんでした")
                            self.browser.save_screenshot("apply_button_not_found")
                            # エラーだが処理を続行
                        else:
                            # 変更が反映されるまで待機
                            self.logger.debug(f"日付変更の反映を待機しています... ({self.page_load_wait}秒)")
                            time.sleep(self.page_load_wait)
                            self.logger.info("「昨日」の日付設定が完了しました")
            # 「昨日」が無効で日付指定がある場合
            elif start_date is not None or end_date is not None:
                self.set_date_range(start_date, end_date)
            else:
                self.logger.info("開始日と終了日が指定されていないため、デフォルトの日付範囲を使用します")
            
            # トラフィックタイプを指定している場合のみタブを選択する
            if traffic_type != "all":
                # トラフィックタイプタブをクリック（該当するセレクタが存在する場合のみ）
                selector_name = f"{traffic_type}_traffic_tab"
                self.logger.info(f"{traffic_type}トラフィックタブを選択します")
                
                # まずセレクタが存在するか確認
                if self.browser.get_element(self.common_selector_group, selector_name, wait_time=2):
                    if not self.browser.click_element_by_selector(self.common_selector_group, selector_name, timeout=self.element_timeout):
                        self.logger.warning(f"{traffic_type}トラフィックタブが見つからないか、クリックできませんでした。全トラフィックタブを試みます。")
                        # 全トラフィックタブを代わりに試す
                        if not self.browser.click_element_by_selector(self.common_selector_group, "all_traffic_tab", timeout=self.element_timeout):
                            self.logger.warning("全トラフィックタブもクリックできませんでした。処理を続行します。")
                            # エラー画面を保存
                            self.browser.save_screenshot(f"{traffic_type}_traffic_tab_not_found")
                else:
                    self.logger.warning(f"{traffic_type}トラフィックタブが存在しません。このステップをスキップします。")
                    self.browser.save_screenshot(f"{traffic_type}_traffic_tab_not_exist")
                    
                # タブ切り替え後の読み込みを待機
                self.logger.debug(f"タブ切り替え後の読み込みを待機しています... ({self.page_load_wait}秒)")
                time.sleep(self.page_load_wait)
            else:
                # 全トラフィックタブをクリック
                self.logger.info("全トラフィックタブを選択します")
                if not self.browser.click_element_by_selector(self.common_selector_group, "all_traffic_tab", timeout=self.element_timeout):
                    self.logger.warning("全トラフィックタブがクリックできませんでした。処理を続行します。")
                    self.browser.save_screenshot("all_traffic_tab_not_found")
                
                # タブ切り替え後の読み込みを待機
                self.logger.debug(f"タブ切り替え後の読み込みを待機しています... ({self.page_load_wait}秒)")
                time.sleep(self.page_load_wait)
            
            # ビューボタンをクリック
            self.logger.info("ビューボタンをクリックします")
            if not self.browser.click_element_by_selector(self.selector_group, "view_button", timeout=self.element_timeout):
                error_msg = "ビューボタンが見つかりませんでした"
                self.logger.error(error_msg)
                self.browser.save_screenshot("view_button_not_found")
                raise CSVDownloadError(error_msg)
                
            # 少し待機してドロップダウンメニューが表示されるのを待つ
            time.sleep(1)
            
            # プログラム用全項目ビューをクリック
            self.logger.info("プログラム用全項目ビューを選択します")
            if not self.browser.click_element_by_selector(self.selector_group, "program_all_view", timeout=self.element_timeout):
                error_msg = "プログラム用全項目ビューが見つかりませんでした"
                self.logger.error(error_msg)
                self.browser.save_screenshot("program_all_view_not_found")
                raise CSVDownloadError(error_msg)
                
            # ビューが適用されるまで待機
            self.logger.debug(f"ビュー適用の反映を待機しています... ({self.page_load_wait}秒)")
            time.sleep(self.page_load_wait)
            
            # 共通のCSVダウンロード処理を呼び出す
            file_pattern = 'detail_analyze'  # 詳細分析レポートの検出パターン
            downloaded_file = self._export_and_download_csv(file_pattern, output_path)
            
            # 詳細分析レポートには日付列を追加
            if csv_type == "detailed_analysis":
                downloaded_file = self._add_date_column(downloaded_file)
            
            return downloaded_file
            
        except Exception as e:
            error_msg = f"CSVダウンロード中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("download_csv_error")
            raise CSVDownloadError(error_msg)

    def download_cv_attribute_csv(self, start_date=None, end_date=None, output_path=None, csv_type="conversion_attribute", use_yesterday=True):
        """
        コンバージョン属性レポートCSVをダウンロードします

        Args:
            start_date (str, optional): 開始日 (YYYY-MM-DD形式)
            end_date (str, optional): 終了日 (YYYY-MM-DD形式)
            output_path (str, optional): ダウンロードしたCSVの保存先パス
            csv_type (str, optional): CSVの種類（デフォルト: "conversion_attribute"）
            use_yesterday (bool, optional): 「昨日」の日付を使用するかどうか（デフォルト: True）

        Returns:
            str: ダウンロードされたCSVファイルのパス

        Raises:
            CSVDownloadError: CSVダウンロード中にエラーが発生した場合
        """
        try:
            date_option = "「昨日」" if use_yesterday else f"{start_date or '指定なし'} から {end_date or '指定なし'}"
            self.logger.info(f"コンバージョン属性レポートCSVのダウンロードを開始します（期間: {date_option}）")
            
            # コンバージョン属性ページに移動
            self._navigate_to_cv_attribute_page()
            
            # 日付範囲を設定
            if use_yesterday:
                self._set_yesterday_for_cv_attribute()
            elif start_date or end_date:
                self._set_date_range_for_cv_attribute(start_date, end_date)
            else:
                self.logger.info("日付範囲の指定がないため、デフォルトの日付範囲を使用します")
            
            # 共通のCSVダウンロード処理を呼び出す
            file_pattern = 'cv_attr'
            return self._export_and_download_csv(file_pattern, output_path)
            
        except CSVDownloadError:
            # 既に詳細なエラーメッセージが記録されている場合は再スロー
            raise
        except Exception as e:
            error_msg = f"コンバージョン属性レポートCSVのダウンロード中に予期しないエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("cv_attribute_csv_unexpected_error")
            raise CSVDownloadError(error_msg) from e
            
    def _set_date_range_for_cv_attribute(self, start_date=None, end_date=None):
        """
        コンバージョン属性レポートの日付範囲を設定します

        Args:
            start_date (str, optional): 開始日（YYYY-MM-DD形式）
            end_date (str, optional): 終了日（YYYY-MM-DD形式）
        """
        if not start_date and not end_date:
            self.logger.info("日付範囲が指定されていないため、デフォルトの日付範囲を使用します")
            return

        try:
            self.logger.info(f"日付範囲を設定します: {start_date} 〜 {end_date}")
            
            # ページが完全に読み込まれてUI要素が利用可能になるまで待機
            self.logger.info("日付操作の前に、UIが完全に読み込まれることを確認します...")
            time.sleep(3)  # 最初に3秒待機して安定させる
            
            # セレクタファイルからセレクタを取得
            date_picker_selector = "cv_attribute_date_picker"
            
            # 日付ピッカー要素が存在するか先に確認
            try:
                date_picker_element = self.browser.get_element("common", date_picker_selector, wait_time=5)
                if date_picker_element:
                    self.logger.info("日付ピッカー要素が見つかりました")
                else:
                    self.logger.warning("日付ピッカー要素が見つかりません。XPATHでの検索を試みます")
            except Exception as e:
                self.logger.warning(f"日付ピッカー要素の検索中にエラー: {e}")
                
            # 日付ピッカーをクリック
            if not self.browser.click_element_by_selector("common", date_picker_selector, wait_time=5, timeout=self.element_timeout):
                self.logger.warning("日付ピッカーセレクタが見つかりませんでした。XPATHを使用して試行します。")
                # セレクタが見つからない場合、XPATHを使用
                date_picker_xpath = "//div[contains(@class, 'date-range-picker') or contains(@class, 'datepicker')]"
                try:
                    element = self.browser.driver.find_element(By.XPATH, date_picker_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して日付ピッカーをクリックしました")
                except Exception as e:
                    self.logger.warning(f"日付ピッカーが見つかりませんでした: {e}。日付設定をスキップします。")
                    return
            
            self.logger.info("日付ピッカーをクリックしました")
            
            # 日付ピッカーが表示されるまで待機
            self.logger.info("日付ピッカーの表示を待機しています...")
            time.sleep(2)
            
            # 日付入力フィールドが表示されるのを待機
            try:
                from selenium.webdriver.common.by import By
                date_input_selector = "input[type='text'], .date-input, [placeholder*='日付']"
                
                if self.browser.wait_for_element(By.CSS_SELECTOR, date_input_selector, timeout=5):
                    self.logger.info("日付入力フィールドが表示されました")
                else:
                    self.logger.warning("日付入力フィールドの表示が確認できませんでしたが処理を続行します")
            except Exception as wait_error:
                self.logger.warning(f"日付入力フィールド待機中にエラー: {wait_error}")
            
            # 開始日を設定
            if start_date:
                if not self.browser.input_text_by_selector("common", "cv_attribute_start_date_input", start_date, clear_first=True, wait_time=3, timeout=self.element_timeout):
                    self.logger.warning("開始日入力フィールドが見つかりませんでした。XPATHを使用して試行します。")
                    # XPATHで検索
                    start_input_xpath = "//input[contains(@id, 'start') or contains(@placeholder, '開始')]"
                    try:
                        element = self.browser.driver.find_element(By.XPATH, start_input_xpath)
                        element.clear()
                        element.send_keys(start_date)
                        self.logger.info(f"XPATHを使用して開始日を設定しました: {start_date}")
                    except Exception as e:
                        self.logger.warning(f"開始日入力フィールドが見つかりませんでした: {e}")
                else:
                    self.logger.info(f"開始日を設定しました: {start_date}")
            
            # 開始日入力後に少し待機
            time.sleep(1)
            
            # 終了日を設定
            if end_date:
                if not self.browser.input_text_by_selector("common", "cv_attribute_end_date_input", end_date, clear_first=True, wait_time=3, timeout=self.element_timeout):
                    self.logger.warning("終了日入力フィールドが見つかりませんでした。XPATHを使用して試行します。")
                    # XPATHで検索
                    end_input_xpath = "//input[contains(@id, 'end') or contains(@placeholder, '終了')]"
                    try:
                        element = self.browser.driver.find_element(By.XPATH, end_input_xpath)
                        element.clear()
                        element.send_keys(end_date)
                        self.logger.info(f"XPATHを使用して終了日を設定しました: {end_date}")
                    except Exception as e:
                        self.logger.warning(f"終了日入力フィールドが見つかりませんでした: {e}")
                else:
                    self.logger.info(f"終了日を設定しました: {end_date}")
            
            # 終了日入力後に少し待機
            time.sleep(1)
            
            # 適用ボタンを押す
            if not self.browser.click_element_by_selector("common", "cv_attribute_date_apply_button", wait_time=3, timeout=self.element_timeout):
                self.logger.warning("適用ボタンが見つかりませんでした。XPATHを使用して試行します。")
                # XPATHで検索
                apply_button_xpath = "//button[contains(text(), '適用') or contains(text(), 'Apply') or contains(@class, 'apply')]"
                try:
                    element = self.browser.driver.find_element(By.XPATH, apply_button_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して日付範囲の適用ボタンをクリックしました")
                except Exception as e:
                    self.logger.warning(f"適用ボタンが見つかりませんでした: {e}。日付設定が適用されていない可能性があります。")
                    return
            else:
                self.logger.info("日付範囲の適用ボタンをクリックしました")
            
            # 日付が適用されるまで十分待機
            self.logger.info("日付範囲の適用を待機しています...")
            time.sleep(3)
            
            # 日付範囲が適用されたか確認する（可能であれば）
            try:
                element = self.browser.get_element("common", "cv_attribute_date_display", wait_time=2)
                if element and element.is_displayed():
                    date_text = element.text
                    self.logger.info(f"設定された日付範囲: {date_text}")
                else:
                    # 確認はできなかったが、エラーにはしない
                    self.logger.info("日付範囲が適用されました（表示確認なし）")
            except Exception as date_check_error:
                self.logger.warning(f"日付範囲の確認中にエラーが発生しましたが、処理を続行します: {date_check_error}")
            
            # ページが更新された場合のための待機
            self.logger.info("日付適用後のページ更新を待機しています...")
            time.sleep(3)
            
            # スクリーンショットを取得
            self.browser.save_screenshot("cv_attribute_date_range_set")
            
        except Exception as e:
            error_msg = f"コンバージョン属性レポートの日付範囲設定中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("cv_attribute_date_range_error")
            # 日付設定エラーはプロセスを停止するほどのエラーではないため、例外を投げずに警告だけ表示
            self.logger.warning("日付範囲設定エラーが発生しましたが、デフォルト範囲で続行します")

    def _set_yesterday_for_cv_attribute(self):
        """
        コンバージョン属性レポートの日付範囲を「昨日」に設定します
        """
        try:
            self.logger.info("コンバージョン属性レポートの日付範囲を「昨日」に設定します")
            
            # ページが完全に読み込まれていることを確認
            time.sleep(3)
            
            # 日付ピッカーをクリック
            self.logger.info("日付ピッカーをクリックします")
            if not self.browser.click_element_by_selector("common", "date_picker_trigger", wait_time=5, timeout=self.element_timeout):
                self.logger.warning("日付ピッカーが見つかりませんでした。XPATHを使用して試行します")
                date_picker_xpath = "//div[contains(@class, 'date-range-picker') or contains(@class, 'datepicker')]"
                try:
                    element = self.browser.driver.find_element(By.XPATH, date_picker_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して日付ピッカーをクリックしました")
                except Exception as e:
                    self.logger.warning(f"日付ピッカーが見つかりませんでした: {e}。日付設定をスキップします。")
                    return
            
            # 日付ピッカーが表示されるまで待機
            self.logger.info("日付ピッカーの表示を待機しています...")
            time.sleep(2)
            
            # 「昨日」を選択
            self.logger.info("「昨日」を選択します")
            if not self.browser.click_element_by_selector("common", "yesterday_date_input", wait_time=3, timeout=self.element_timeout):
                self.logger.warning("「昨日」の選択肢が見つかりませんでした")
                self.browser.save_screenshot("yesterday_option_not_found")
                
                # 要素が見つからない場合はXPATHで試す
                try:
                    yesterday_xpath = "//div[contains(@class, 'side-panel-item') and (contains(text(), '昨日') or contains(text(), 'Yesterday'))]"
                    element = self.browser.driver.find_element(By.XPATH, yesterday_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して「昨日」をクリックしました")
                except Exception as e:
                    self.logger.warning(f"XPATHでも「昨日」が見つかりませんでした: {e}")
                    return
            
            # 適用ボタンをクリック
            self.logger.info("適用ボタンをクリックします")
            if not self.browser.click_element_by_selector("common", "apply_button", wait_time=3, timeout=self.element_timeout):
                self.logger.warning("適用ボタンが見つかりませんでした。XPATHを使用して試行します。")
                # XPATHで検索
                apply_button_xpath = "//button[contains(text(), '適用') or contains(text(), 'Apply') or contains(@class, 'apply')]"
                try:
                    element = self.browser.driver.find_element(By.XPATH, apply_button_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して適用ボタンをクリックしました")
                except Exception as e:
                    self.logger.warning(f"適用ボタンが見つかりませんでした: {e}。日付設定が適用されていない可能性があります。")
                    return
            
            # 日付が適用されるまで待機
            self.logger.info("日付範囲の適用を待機しています...")
            time.sleep(3)
            
            self.logger.info("「昨日」の日付設定が完了しました")
            
        except Exception as e:
            self.logger.warning(f"「昨日」の日付設定中にエラーが発生しました: {e}")
            self.browser.save_screenshot("set_yesterday_error_cv_attribute")
            # エラーをスローしない（処理を継続）

    def _add_date_column(self, csv_file_path: str) -> str:
        """
        CSVファイルのA列に日付列を追加します
        
        Args:
            csv_file_path (str): 処理するCSVファイルのパス
            
        Returns:
            str: 処理後のCSVファイルのパス
        """
        self.logger.info(f"CSVファイルに日付列を追加します: {csv_file_path}")
        
        # 前日の日付をYYYY-MM-DD形式で取得
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.logger.debug(f"使用する日付: {yesterday}")
        
        # 一時ファイルのパスを生成
        temp_file_path = f"{csv_file_path}.temp"
        
        try:
            # CSVファイルの文字コードを検出
            encoding = self._detect_csv_encoding(csv_file_path)
            
            # CSVファイルを開いて内容を読み込む
            with open(csv_file_path, 'r', encoding=encoding, newline='') as csv_in:
                csv_reader = csv.reader(csv_in)
                
                # 一時ファイルに書き込む
                with open(temp_file_path, 'w', encoding=encoding, newline='') as csv_out:
                    csv_writer = csv.writer(csv_out)
                    
                    # 各行を処理
                    for i, row in enumerate(csv_reader):
                        if i == 0:
                            # ヘッダ行の場合は「日付」列を追加
                            new_row = ['日付'] + row
                        else:
                            # データ行の場合は前日の日付を追加
                            new_row = [yesterday] + row
                        
                        # 新しい行を書き込む
                        csv_writer.writerow(new_row)
            
            # 元のファイルを置き換える
            os.remove(csv_file_path)
            os.rename(temp_file_path, csv_file_path)
            
            self.logger.info(f"CSVファイルに日付列を追加しました: {csv_file_path}")
            return csv_file_path
            
        except Exception as e:
            self.logger.error(f"CSVファイルの加工中にエラーが発生しました: {e}")
            # 一時ファイルが残っていれば削除
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                    
            # 元のファイルをそのまま返す
            return csv_file_path
    
    def _detect_csv_encoding(self, file_path: str) -> str:
        """
        CSVファイルの文字コードを検出します
        
        Args:
            file_path (str): CSVファイルのパス
            
        Returns:
            str: 検出された文字コード
        """
        # デフォルトの文字コード
        default_encoding = 'cp932'
        
        try:
            # chardetライブラリがあればそれを使用
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    result = chardet.detect(f.read())
                    detected_encoding = result['encoding']
                    confidence = result['confidence']
                    
                    self.logger.debug(f"検出された文字コード: {detected_encoding}, 信頼度: {confidence}")
                    
                    # 信頼度が低い場合はデフォルトを使用
                    if confidence < 0.7:
                        self.logger.warning(f"文字コード検出の信頼度が低いためデフォルトを使用: {default_encoding}")
                        return default_encoding
                        
                    return detected_encoding
            except ImportError:
                pass
                
            # 簡易的な文字コード判定（UTF-8, SJIS, EUC-JP を試す）
            encodings_to_try = ['utf-8', 'cp932', 'euc_jp']
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read()
                        self.logger.debug(f"文字コード {encoding} で正常に読み込めました")
                        return encoding
                except UnicodeDecodeError:
                    continue
            
            self.logger.warning(f"文字コードを特定できなかったためデフォルトを使用: {default_encoding}")
            return default_encoding
            
        except Exception as e:
            self.logger.error(f"文字コード検出中にエラー: {e}")
            return default_encoding