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
        self.download_timeout = int(download_wait)
        
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
            
            # ページのコンテンツが読み込まれるまで少し待機
            time.sleep(2)
            
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
            
    def download_csv(
        self,
        csv_type: str,
        output_path: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        traffic_type: str = "all",
    ) -> str:
        """
        詳細分析画面からCSVをダウンロードします。

        Args:
            csv_type (str): ダウンロードするCSVの種類 ("detailed_analysis" のみサポート)
            output_path (Optional[str], optional): 出力先パス. Defaults to None.
            start_date (Optional[str], optional): 開始日 (YYYY-MM-DD形式). Defaults to None.
            end_date (Optional[str], optional): 終了日 (YYYY-MM-DD形式). Defaults to None.
            traffic_type (str, optional): トラフィックタイプ. Defaults to "all".

        Returns:
            str: ダウンロードしたCSVファイルのパス

        Raises:
            CSVDownloadError: CSVダウンロード中にエラーが発生した場合
        """
        try:
            self.logger.info(f"{csv_type} CSVのダウンロードを開始します")
            
            # 分析ページに移動
            self.navigate_to_analysis_page()
            
            # 日付範囲を設定（両方Noneの場合はデフォルト値を使用するため設定不要）
            if start_date is not None or end_date is not None:
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
            
            # エクスポートボタンをクリック
            self.logger.info("エクスポートボタンをクリックします")
            if not self.browser.click_element_by_selector(self.selector_group, "export_button", timeout=self.element_timeout):
                error_msg = "エクスポートボタンが見つかりませんでした"
                self.logger.error(error_msg)
                self.browser.save_screenshot("export_button_not_found")
                raise CSVDownloadError(error_msg)
                
            # 少し待機してエクスポートメニューが表示されるのを待つ
            time.sleep(1)
            
            # 表を出力（CSV）をクリック
            self.logger.info("表を出力（CSV）ボタンをクリックします")
            try:
                if not self.browser.click_element_by_selector(self.common_selector_group, "csv_download_button", timeout=self.element_timeout):
                    error_msg = "表を出力（CSV）ボタンが見つかりませんでした"
                    self.logger.error(error_msg)
                    self.browser.save_screenshot("csv_download_button_not_found")
                    raise CSVDownloadError(error_msg)
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
            
            # ダウンロード前のファイルリストを取得（比較用）
            pre_download_files = set()
            file_pattern = 'detail_analyze'  # 詳細分析レポートの検出パターン
            
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
                        # ファイル名に'detail_analyze'を含むファイルをフィルタリング
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
                # ブラウザの最新ダウンロードを取得
                try:
                    self.logger.warning("ポーリングでファイルが見つかりませんでした。Browser.get_latest_download()を試行します...")
                    downloaded_file = self.browser.get_latest_download(download_dir=default_download_dir, file_types=['csv'])
                    
                    if downloaded_file and os.path.exists(downloaded_file):
                        found_file = downloaded_file
                        self.logger.info(f"Browser.get_latest_downloadで検出したファイル: {found_file}")
                    else:
                        self.logger.error("ダウンロードファイルが見つかりませんでした")
                        self.browser.save_screenshot("csv_download_not_found")
                        raise CSVDownloadError("ダウンロードファイルが見つかりませんでした")
                except Exception as e:
                    self.logger.error(f"ダウンロード検出の最終試行でエラー: {e}")
                    self.browser.save_screenshot("csv_download_detection_error")
                    raise CSVDownloadError(f"ダウンロードファイル検出中にエラー: {e}")
            
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
                
                # フォルダはself.download_dirを使用
                if csv_type == "detailed_analysis":
                    # 詳細分析レポートの場合
                    target_file = os.path.join(self.download_dir, f"{today}_ebis_detailed_report.csv")
                else:
                    # その他のレポートタイプの場合
                    target_file = os.path.join(self.download_dir, f"{today}_ebis_{csv_type}_report.csv")
            
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
            
    def download_cv_attribute_csv(self, start_date=None, end_date=None, output_path=None, csv_type="conversion_attribute"):
        """
        コンバージョン属性レポートCSVをダウンロードします

        Args:
            start_date (str, optional): 開始日 (YYYY-MM-DD形式)
            end_date (str, optional): 終了日 (YYYY-MM-DD形式)
            output_path (str, optional): ダウンロードしたCSVの保存先パス
            csv_type (str, optional): CSVの種類（デフォルト: "conversion_attribute"）

        Returns:
            str: ダウンロードされたCSVファイルのパス

        Raises:
            CSVDownloadError: CSVダウンロード中にエラーが発生した場合
        """
        try:
            self.logger.info(f"コンバージョン属性レポートCSVのダウンロードを開始します（期間: {start_date or '指定なし'} から {end_date or '指定なし'}）")
            
            # コンバージョン属性ページに移動
            self._navigate_to_cv_attribute_page()
            
            # 日付範囲を設定（指定されている場合）
            if start_date or end_date:
                self._set_date_range_for_cv_attribute(start_date, end_date)
            else:
                self.logger.info("日付範囲の指定がないため、デフォルトの日付範囲を使用します")
                
            # CSVダウンロードボタンをクリック
            self._click_cv_attribute_csv_download_button()
            
            # ダウンロードの完了を待機
            self.logger.debug(f"ダウンロードの完了を待機しています... ({self.download_timeout}秒)")
            
            # ユーザーのデフォルトダウンロードディレクトリを取得
            default_download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(default_download_dir):
                self.logger.warning(f"デフォルトダウンロードディレクトリが存在しません: {default_download_dir}")
                raise CSVDownloadError(f"デフォルトダウンロードディレクトリが見つかりません: {default_download_dir}")
            
            # ダウンロード前のファイルリストを取得（比較用）
            pre_download_files = set()
            file_pattern = 'cv_attr'  # コンバージョン属性レポートの検出パターン
            
            try:
                pre_download_files = set([f for f in os.listdir(default_download_dir) 
                                      if os.path.isfile(os.path.join(default_download_dir, f)) and f.lower().endswith('.csv')])
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
                                      if os.path.isfile(os.path.join(default_download_dir, f)) and f.lower().endswith('.csv')])
                    
                    # ダウンロード前に存在しなかった新しいファイルを探す
                    new_files = current_files - pre_download_files
                    
                    # 新しいファイルが見つかった場合、パターンでフィルタリング
                    if new_files:
                        # ファイル名に'cv_attr'を含むファイルをフィルタリング
                        matching_files = [f for f in new_files if file_pattern.lower() in f.lower()]
                        
                        if matching_files:
                            # 最新のファイルを取得（作成日時でソート）
                            found_file = max(matching_files, key=lambda f: os.path.getctime(os.path.join(default_download_dir, f)))
                            found_file = os.path.join(default_download_dir, found_file)
                            self.logger.info(f"ダウンロードファイルを検出しました: {found_file}")
                            break
                        else:
                            # cv_attrで見つからない場合、新しいCSVファイルをそのまま使用（タイムアウト間際の場合）
                            elapsed = time.time() - start_time
                            if elapsed > self.download_timeout * 0.8:  # 80%の時間経過したら、とりあえず新しいファイルを使う
                                self.logger.warning(f"パターン'{file_pattern}'に一致するファイルが見つかりませんが、新しいCSVファイルが検出されました。これを使用します。")
                                # 最新のファイルを取得
                                found_file = max(new_files, key=lambda f: os.path.getctime(os.path.join(default_download_dir, f)))
                                found_file = os.path.join(default_download_dir, found_file)
                                self.logger.info(f"パターンに一致しないがダウンロードファイルと判断: {found_file}")
                                break
                            else:
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
                # ブラウザの最新ダウンロードを取得
                try:
                    self.logger.warning("ポーリングでファイルが見つかりませんでした。Browser.get_latest_download()を試行します...")
                    downloaded_file = self.browser.get_latest_download(download_dir=default_download_dir, file_types=['csv'])
                    
                    if downloaded_file and os.path.exists(downloaded_file):
                        found_file = downloaded_file
                        self.logger.info(f"Browser.get_latest_downloadで検出したファイル: {found_file}")
                    else:
                        self.logger.error("ダウンロードファイルが見つかりませんでした")
                        self.browser.save_screenshot("cv_attribute_csv_download_not_found")
                        raise CSVDownloadError("ダウンロードファイルが見つかりませんでした")
                except Exception as e:
                    self.logger.error(f"ダウンロード検出の最終試行でエラー: {e}")
                    self.browser.save_screenshot("cv_attribute_csv_download_detection_error")
                    raise CSVDownloadError(f"ダウンロードファイル検出中にエラー: {e}")
            
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
                
                # フォルダはself.download_dirを使用
                target_file = os.path.join(self.download_dir, f"{today}_ebis_conversion_attribute.csv")
            
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
                
                # コンバージョン属性レポートでは日付列の追加は不要
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
            
            # セレクタファイルからセレクタを取得
            date_picker_selector = "cv_attribute_date_picker"
            
            # 日付ピッカーをクリック
            if not self.browser.click_element_by_selector("common", date_picker_selector, timeout=self.element_timeout):
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
            time.sleep(1)
            
            # 開始日を設定
            if start_date:
                if not self.browser.input_text_by_selector("common", "cv_attribute_start_date_input", start_date, clear_first=True, timeout=self.element_timeout):
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
            
            # 終了日を設定
            if end_date:
                if not self.browser.input_text_by_selector("common", "cv_attribute_end_date_input", end_date, clear_first=True, timeout=self.element_timeout):
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
            
            # 適用ボタンを押す
            if not self.browser.click_element_by_selector("common", "cv_attribute_date_apply_button", timeout=self.element_timeout):
                self.logger.warning("適用ボタンが見つかりませんでした。XPATHを使用して試行します。")
                # XPATHで検索
                apply_button_xpath = "//button[contains(text(), '適用') or contains(text(), 'Apply') or contains(@class, 'apply')]"
                try:
                    element = self.browser.driver.find_element(By.XPATH, apply_button_xpath)
                    element.click()
                    self.logger.info("XPATHを使用して日付範囲の適用ボタンをクリックしました")
                except Exception as e:
                    self.logger.warning(f"適用ボタンが見つかりませんでした: {e}。日付設定が適用されていない可能性があります。")
            else:
                self.logger.info("日付範囲の適用ボタンをクリックしました")
            
            # 日付が適用されるまで待機
            time.sleep(2)
            
            # 日付範囲が適用されたか確認する（可能であれば）
            try:
                element = self.browser.get_element("common", "cv_attribute_date_display", wait_time=1)
                if element and element.is_displayed():
                    date_text = element.text
                    self.logger.info(f"設定された日付範囲: {date_text}")
                else:
                    # 確認はできなかったが、エラーにはしない
                    self.logger.info("日付範囲が適用されました（表示確認なし）")
            except Exception as date_check_error:
                self.logger.warning(f"日付範囲の確認中にエラーが発生しましたが、処理を続行します: {date_check_error}")
            
        except Exception as e:
            error_msg = f"コンバージョン属性レポートの日付範囲設定中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("cv_attribute_date_range_error")
            # 日付設定エラーはプロセスを停止するほどのエラーではないため、例外を投げずに警告だけ表示
            self.logger.warning("日付範囲設定エラーが発生しましたが、デフォルト範囲で続行します")

    def _click_cv_attribute_csv_download_button(self):
        """
        コンバージョン属性レポートのCSVダウンロードボタンをクリックします
        """
        try:
            self.logger.info("CSVダウンロードボタンをクリックします")
            
            # CV属性ページ用のCSVボタンセレクタを使用
            if not self.browser.click_element_by_selector("cv_attribute", "csv_button", timeout=self.element_timeout):
                self.logger.warning("CV属性ページ用のCSVボタンが見つかりませんでした。他の方法を試します。")
                
                # 共通セレクタグループのdownload_buttonを試す
                if not self.browser.click_element_by_selector("common", "download_button", timeout=self.element_timeout):
                    self.logger.warning("共通ダウンロードボタンも見つかりませんでした。XPATHを使用して試行します。")
                    
                    # CSSセレクタを試す 
                    try:
                        css_selector = "#common-bar > div.clearfix.common-bar > nav > div.navbar-nav > div.dropdown.nav-link.nav-link--icon > div > span > i"
                        element = self.browser.driver.find_element(By.CSS_SELECTOR, css_selector)
                        element.click()
                        self.logger.info("CSSセレクタを使用してCSVダウンロードボタンをクリックしました")
                        
                        # ドロップダウンメニューが表示されるまで待機
                        time.sleep(1)
                        
                        # CSVダウンロードのオプションをクリック
                        try:
                            csv_option = self.browser.driver.find_element(By.CSS_SELECTOR, ".dropdown-menu.show .dropdown-item")
                            csv_option.click()
                            self.logger.info("CSVダウンロードオプションをクリックしました")
                        except Exception as option_error:
                            self.logger.warning(f"CSVダウンロードオプションが見つかりませんでした: {option_error}")
                            # 画面のスクリーンショットを取得
                            self.browser.save_screenshot("csv_download_option_not_found")
                            raise
                    except Exception as e:
                        # 最後の手段としてXPATHを使用
                        self.logger.warning(f"CSSセレクタも見つかりませんでした: {e}")
                        try:
                            # セレクタがない場合はXPATHで検索してクリック - selectorsで定義された値を直接使用
                            download_button_xpath = "//*[@id=\"common-bar\"]/div[2]/nav/div[2]/div[4]/div[1]"
                            element = self.browser.driver.find_element(By.XPATH, download_button_xpath)
                            element.click()
                            self.logger.info("XPATHを使用してCSVダウンロードボタンをクリックしました")
                        except Exception as xpath_error:
                            error_msg = f"CSVダウンロードボタンが見つかりませんでした: 複数の検索方法を試行しましたが失敗しました"
                            self.logger.error(error_msg)
                            self.browser.save_screenshot("cv_attribute_csv_button_not_found")
                            raise CSVDownloadError(error_msg)
                else:
                    self.logger.info("共通ダウンロードボタンをクリックしました")
                    
                    # ドロップダウンメニューが表示されるまで待機
                    time.sleep(1)
                    
                    # CSVダウンロードオプションをクリック
                    if not self.browser.click_element_by_selector("common", "csv_download_button", timeout=self.element_timeout):
                        self.logger.warning("CSVダウンロードオプションが見つかりませんでした")
                        self.browser.save_screenshot("csv_download_option_not_found")
                    else:
                        self.logger.info("CSVダウンロードオプションをクリックしました")
            else:
                self.logger.info("CV属性ページのCSVボタンをクリックしました")
            
            # ダウンロードダイアログが表示される場合は処理
            try:
                # ダウンロード確認ダイアログが表示されるかチェック (1秒だけ待機)
                element = self.browser.get_element("common", "cv_attribute_download_confirm_dialog", wait_time=1)
                if element and element.is_displayed():
                    # 確認ボタンをクリック
                    if not self.browser.click_element_by_selector("common", "cv_attribute_download_confirm_button", timeout=self.element_timeout):
                        self.logger.warning("確認ボタンのセレクタが見つかりませんでした。XPATHを使用して試行します。")
                        # セレクタがない場合はXPATHで検索
                        confirm_button_xpath = "//button[contains(text(), '確認') or contains(text(), 'OK') or contains(@class, 'confirm')]"
                        try:
                            confirm_button = self.browser.driver.find_element(By.XPATH, confirm_button_xpath)
                            confirm_button.click()
                            self.logger.info("XPATHを使用してダウンロード確認ダイアログでOKボタンをクリックしました")
                        except Exception as btn_error:
                            self.logger.warning(f"確認ボタンが見つかりませんでした: {btn_error}。ダウンロードが開始されない可能性があります。")
                    else:
                        self.logger.info("ダウンロード確認ダイアログでOKボタンをクリックしました")
            except Exception as dialog_error:
                # ダイアログが表示されない場合は警告だけ出して続行
                self.logger.info(f"ダウンロード確認ダイアログは表示されませんでした: {dialog_error}")
            
            # ダウンロードが開始されるまで待機
            time.sleep(2)
            self.logger.info("CSVダウンロードを開始しました")
            
        except Exception as e:
            error_msg = f"コンバージョン属性レポートのCSVダウンロードボタンクリック中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.browser.save_screenshot("cv_attribute_csv_download_error")
            raise CSVDownloadError(error_msg) from e 