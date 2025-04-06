#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト結果サマリー生成ユーティリティ

tests/resultsディレクトリに保存されたテスト結果を集約し、
担保された機能の一覧を表形式で表示します。
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import glob
from typing import Dict, Optional, Any, List, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class TestSummaryGenerator:
    """テスト結果サマリー生成クラス"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        初期化

        Args:
            project_root (Optional[Path]): プロジェクトルートパス。指定しない場合は自動検出
        """
        # プロジェクトルートのパスを取得
        if project_root:
            self.project_root = project_root
        else:
            # utils/test_summary.py の場合、ルートは2階層上
            self.project_root = Path(__file__).resolve().parent.parent.parent
            
        self.results_dir = self.project_root / "tests" / "results"
        
    def get_test_results(self) -> Optional[Dict[str, Any]]:
        """
        テスト結果ファイルからデータを収集
        
        Returns:
            Optional[Dict[str, Any]]: テスト結果の辞書、失敗時はNone
        """
        # 結果ディレクトリが存在しない場合
        if not self.results_dir.exists():
            logger.error(f"テスト結果ディレクトリ {self.results_dir} が見つかりません")
            return None
            
        # JSONファイルを探す
        result_files = list(self.results_dir.glob("*.json"))
        
        if not result_files:
            logger.error(f"{self.results_dir} にテスト結果ファイルが見つかりません")
            return None
            
        # すべての結果を集約
        all_results = {}
        file_count = 0
        
        for result_file in result_files:
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    file_count += 1
                    
                    # データをマージ
                    for test_name, result in data.items():
                        # ファイル名をキーに追加
                        test_key = f"{result_file.stem}::{test_name}"
                        all_results[test_key] = result
                        
            except Exception as e:
                logger.warning(f"{result_file} の読み込みに失敗しました: {e}")
                
        if file_count == 0:
            logger.error("有効なテスト結果ファイルが見つかりませんでした")
            return None
            
        logger.info(f"{file_count}個のテスト結果ファイルから{len(all_results)}個のテスト結果を読み込みました")
        return all_results
    
    def get_summary_stats(self, results: Dict[str, Any]) -> Tuple[int, int, int, float]:
        """
        テスト結果の統計情報を取得
        
        Args:
            results (Dict[str, Any]): テスト結果の辞書
            
        Returns:
            Tuple[int, int, int, float]: (全体数, 成功数, 失敗数, 成功率)
        """
        if not results:
            return (0, 0, 0, 0.0)
            
        passed_count = sum(1 for data in results.values() if data.get("passed", False))
        total = len(results)
        failed_count = total - passed_count
        
        pass_rate = (passed_count / total) * 100 if total > 0 else 0.0
        
        return (total, passed_count, failed_count, pass_rate)
    
    def generate_summary(self, results: Optional[Dict[str, Any]] = None) -> bool:
        """
        テスト結果のサマリーを生成して表示
        
        Args:
            results (Optional[Dict[str, Any]]): テスト結果の辞書。指定しない場合は取得
        
        Returns:
            bool: 成功時はTrue、失敗時はFalse
        """
        if results is None:
            results = self.get_test_results()
            
        if not results:
            return False
            
        print("\n" + "=" * 100)
        print(" " * 35 + "TEST RESULT SUMMARY (" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")")
        print("=" * 100)
        
        # ヘッダー
        print(f"{'TEST NAME':<60}{'RESULT':<10}{'FUNCTIONALITY ASSURED'}")
        print("-" * 100)
        
        # 結果をソートして表示
        passed_count = 0
        failed_count = 0
        
        for test_key, data in sorted(results.items()):
            status = "PASS" if data.get("passed", False) else "FAIL"
            
            # テスト名を整形（ファイル名とテスト名を分離）
            parts = test_key.split("::")
            test_name = parts[-1]
            
            if len(parts) > 1:
                # ファイルが含まれている場合、短く整形
                file_name = parts[0].replace("_test_results", "").replace("_", " ")
                display_name = f"{file_name} > {test_name}"
            else:
                display_name = test_name
                
            # 60文字までに切り詰め
            if len(display_name) > 57:
                display_name = display_name[:54] + "..."
                
            description = data.get("description", "No description")
            print(f"{display_name:<60}{status:<10}{description}")
            
            if data.get("passed", False):
                passed_count += 1
            else:
                failed_count += 1
        
        total = passed_count + failed_count
        
        # フッター
        print("-" * 100)
        print(f"Total: {total} tests ({passed_count} passed / {failed_count} failed)")
        
        if total > 0:
            pass_rate = (passed_count / total) * 100
            print(f"Success rate: {pass_rate:.1f}%")
        
        print("=" * 100)
        return True
    
    def export_summary(self, output_path: Optional[Path] = None, format: str = "json") -> Optional[Path]:
        """
        テスト結果のサマリーをファイルに出力
        
        Args:
            output_path (Optional[Path]): 出力ファイルパス。指定しない場合は自動生成
            format (str): 出力形式 ("json" または "txt")
            
        Returns:
            Optional[Path]: 出力ファイルパス、失敗時はNone
        """
        results = self.get_test_results()
        if not results:
            return None
            
        if output_path is None:
            # 自動生成
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format.lower() == "json":
                output_path = self.project_root / "tests" / "results" / f"summary_{date_str}.json"
            else:
                output_path = self.project_root / "tests" / "results" / f"summary_{date_str}.txt"
        
        try:
            # 出力ディレクトリの確認
            output_dir = output_path.parent
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
                
            if format.lower() == "json":
                # JSON形式で出力
                stats = self.get_summary_stats(results)
                summary_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_tests": stats[0],
                    "passed_tests": stats[1],
                    "failed_tests": stats[2],
                    "pass_rate": stats[3],
                    "results": results
                }
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)
                    
            else:
                # テキスト形式で出力
                stats = self.get_summary_stats(results)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("=" * 80 + "\n")
                    f.write(" " * 25 + "TEST RESULT SUMMARY (" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
                    f.write("=" * 80 + "\n\n")
                    
                    f.write(f"{'TEST NAME':<60}{'RESULT':<10}{'FUNCTIONALITY ASSURED'}\n")
                    f.write("-" * 80 + "\n")
                    
                    for test_key, data in sorted(results.items()):
                        status = "PASS" if data.get("passed", False) else "FAIL"
                        parts = test_key.split("::")
                        test_name = parts[-1]
                        
                        if len(parts) > 1:
                            file_name = parts[0].replace("_test_results", "").replace("_", " ")
                            display_name = f"{file_name} > {test_name}"
                        else:
                            display_name = test_name
                            
                        if len(display_name) > 57:
                            display_name = display_name[:54] + "..."
                            
                        description = data.get("description", "No description")
                        f.write(f"{display_name:<60}{status:<10}{description}\n")
                    
                    f.write("-" * 80 + "\n")
                    f.write(f"Total: {stats[0]} tests ({stats[1]} passed / {stats[2]} failed)\n")
                    f.write(f"Success rate: {stats[3]:.1f}%\n")
                    f.write("=" * 80 + "\n")
            
            logger.info(f"テスト結果サマリーを {output_path} に保存しました")
            return output_path
                
        except Exception as e:
            logger.error(f"テスト結果の保存に失敗しました: {e}")
            return None
            
    def detailed_summary(self, results: Optional[Dict[str, Any]] = None, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        テスト結果の詳細サマリーを生成し、対応ファイル、メソッド、機能を含める
        
        Args:
            results (Optional[Dict[str, Any]]): テスト結果の辞書。指定しない場合は取得
            output_path (Optional[Path]): 出力ファイルパス。指定しない場合は自動生成
            
        Returns:
            Optional[Path]: 出力ファイルパス、失敗時はNone
        """
        if results is None:
            results = self.get_test_results()
            
        if not results:
            return None
            
        # テスト対応ファイルとメソッドのマッピング（実際のプロジェクトでは動的に生成する）
        test_file_method_map = {
            # アクセステスト系
            "プロジェクト構造確認": {"file": "src/utils/environment.py", "method": "get_project_root()", "function": "基本ディレクトリ構造が適切で、アプリケーションが正しく実行できる環境が整っている"},
            "モジュール構造確認": {"file": "src/modules/*", "method": "各種モジュール検証", "function": "ビジネスロジックモジュールの構造が維持され、機能拡張時の整合性が担保されている"},
            "ユーティリティ確認": {"file": "src/utils/*", "method": "各種ユーティリティ関数", "function": "共通ユーティリティが適切に構成され、環境管理とロギング機能が利用可能な状態にある"},
            "ログディレクトリ確認": {"file": "src/utils/logging_config.py", "method": "get_logger()", "function": "ログ出力先が確保され、アプリケーションの動作ログが適切に記録できる"},
            "設定ファイル確認": {"file": "src/utils/environment.py", "method": "get_config_value()", "function": "環境変数と設定ファイルが正しく配置され、アプリケーションが設定を適切に読み込める"},
            
            # Seleniumログインテスト系
            "test_browser_selectors_initialization": {"file": "src/modules/selenium/browser.py", "method": "_load_selectors()", "function": "セレクタCSVファイルが正しく読み込まれ、ログイン用セレクタが適切に初期化される"},
            "test_httpbin_form_submission": {"file": "src/modules/selenium/browser.py", "method": "navigate_to(), find_element()", "function": "外部サイトへのフォーム送信とレスポンス検証が正常に行える"},
            "test_dummy_login_page": {"file": "src/modules/selenium/browser.py", "method": "execute_script(), analyze_page_content()", "function": "JavaScriptでのログインフォーム操作とアラート処理が適切に実行できる"},
            
            # ログインページ解析テスト系
            "test_login_form_detection": {"file": "src/modules/selenium/browser.py", "method": "analyze_page_content()", "function": "ログインフォームを自動的に検出し、入力フィールドやボタンを識別できる"},
            "test_login_failure_detection": {"file": "src/modules/selenium/browser.py", "method": "analyze_page_content(), find_element_by_text()", "function": "ログイン失敗時のエラーメッセージを適切に検出できる"},
            "test_login_security_features": {"file": "src/modules/selenium/browser.py", "method": "get_page_source()", "function": "HTTPS、CSRF対策、二要素認証などのセキュリティ機能の有無を検出できる"},
            "test_login_page_performance": {"file": "src/modules/selenium/browser.py", "method": "_get_page_status()", "function": "ページロード時間の計測とパフォーマンス検証が適切に行える"},
            "test_login_success_workflow": {"file": "src/modules/selenium/browser.py", "method": "wait_for_page_load(), find_element_by_text()", "function": "ログイン成功後の画面遷移と成功メッセージを正しく検証できる"},
            
            # ページ解析テスト系
            "test_basic_page_analysis": {"file": "src/modules/selenium/browser.py", "method": "analyze_page_content(), _get_page_status()", "function": "基本的なページ構造解析機能を検証"},
            "test_form_automation": {"file": "src/modules/selenium/browser.py", "method": "find_element(), wait_for_element()", "function": "フォームの自動入力と送信機能を検証"},
            "test_search_elements_by_text": {"file": "src/modules/selenium/browser.py", "method": "find_element_by_text()", "function": "テキスト内容による要素検索機能を検証"},
            "test_interactive_elements": {"file": "src/modules/selenium/browser.py", "method": "find_interactive_elements()", "function": "インタラクティブ要素の識別機能を検証"},
            "test_page_state_detection": {"file": "src/modules/selenium/browser.py", "method": "detect_page_changes()", "function": "ページの状態検出機能を検証"},
            
            # Google Cloud認証テスト系
            "test_dataset_exists": {"file": "src/utils/bigquery.py", "method": "dataset_exists()", "function": "BigQueryのデータセットが存在するか確認する"},
            "test_table_exists": {"file": "src/utils/bigquery.py", "method": "table_exists()", "function": "BigQueryのテーブルが存在するか確認する"},
            "test_get_table_schema": {"file": "src/utils/bigquery.py", "method": "get_table_schema()", "function": "BigQueryのテーブルスキーマを取得できるか確認する"},
            "test_credentials_loading": {"file": "src/utils/bigquery.py", "method": "get_credentials()", "function": "サービスアカウント認証情報が適切に読み込めるか確認する"},
            "test_query_execution": {"file": "src/utils/bigquery.py", "method": "run_query()", "function": "基本的なSQLクエリが実行できるか確認する"},
            
            # エラー処理テスト系
            "test_nonexistent_page": {"file": "src/modules/selenium/browser.py", "method": "navigate_to(), handle_error()", "function": "存在しないページへのアクセス時のエラー処理を検証"},
            "test_invalid_protocol": {"file": "src/modules/selenium/browser.py", "method": "navigate_to(), handle_error()", "function": "無効なプロトコルのURLへのアクセス時のエラー処理を検証"},
            "test_page_with_errors": {"file": "src/modules/selenium/browser.py", "method": "analyze_page_content(), handle_error()", "function": "エラーが含まれるページの処理を検証"},
            "test_redirect_handling": {"file": "src/modules/selenium/browser.py", "method": "navigate_to(), detect_redirects()", "function": "リダイレクトの適切な処理を検証"},
            "test_slow_loading_page": {"file": "src/modules/selenium/browser.py", "method": "wait_for_page_load()", "function": "遅いページ読み込みの適切な処理を検証"},
            "test_alert_and_confirm_dialogs": {"file": "src/modules/selenium/browser.py", "method": "_check_alerts(), handle_dialog()", "function": "アラートと確認ダイアログの適切な処理を検証"}
        }
        
        if output_path is None:
            # 自動生成
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.project_root / "tests" / "results" / f"detailed_summary_{date_str}.txt"
        
        try:
            # 出力ディレクトリの確認
            output_dir = output_path.parent
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
                
            # 統計情報の取得
            stats = self.get_summary_stats(results)
            
            # テスト結果をグループ化
            grouped_results = {}
            
            for test_key, data in results.items():
                parts = test_key.split("::")
                test_name = parts[-1]
                
                if len(parts) > 1:
                    group_name = parts[0].replace("_test_results", "").replace("_", " ")
                else:
                    group_name = "その他"
                    
                if group_name not in grouped_results:
                    grouped_results[group_name] = []
                    
                grouped_results[group_name].append({
                    "name": test_name,
                    "passed": data.get("passed", False),
                    "description": data.get("description", "No description"),
                    "error_message": data.get("error_message", ""),
                    "fix_suggestion": data.get("fix_suggestion", ""),
                    "data": data
                })
            
            # 詳細サマリーを生成
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "テスト実行結果サマリー (" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
                f.write("=" * 80 + "\n\n")
                
                # 環境情報
                f.write("【実行環境情報】\n")
                f.write("環境: Windows 10\n")
                f.write("Python: 3.x\n")
                f.write("仮想環境: venv\n")
                f.write("実行日時: " + datetime.now().strftime("%Y-%m-%d") + "\n\n")
                
                # 統計情報
                f.write("【テスト実行状況】\n")
                total_tests = stats[0]
                passed_tests = stats[1]
                failed_tests = stats[2]
                pass_rate = stats[3]
                f.write(f"実行テスト数: {total_tests}件\n")
                f.write(f"成功: {passed_tests}件\n")
                f.write(f"失敗: {failed_tests}件\n")
                f.write(f"成功率: {pass_rate:.1f}%\n\n")
                
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "テスト結果詳細 - 成功したテスト\n")
                f.write("=" * 80 + "\n\n")
                
                # グループごとに結果を表示
                for group_idx, (group_name, tests) in enumerate(sorted(grouped_results.items()), 1):
                    # グループ内で成功したテストの数を集計
                    passed_in_group = sum(1 for test in tests if test["passed"])
                    total_in_group = len(tests)
                    
                    # 成功したテストが1件以上ある場合のみグループを表示
                    if passed_in_group > 0:
                        f.write(f"{group_idx}. {group_name} (tests/results/{group_name.lower().replace(' ', '_')}_test_results.json)\n")
                        f.write("-" * 80 + "\n")
                        f.write(f"ステータス: {'成功' if passed_in_group == total_in_group else '一部成功'} ({passed_in_group}/{total_in_group}テスト成功)\n\n")
                        
                        # テーブルヘッダー
                        f.write(f"{'テスト名':<25}{'対応ファイル':<35}{'メソッド':<30}{'検証機能'}\n")
                        f.write("-" * 80 + "\n")
                        
                        # 成功したテストのみを表示
                        passed_tests_list = [test for test in tests if test["passed"]]
                        for test in sorted(passed_tests_list, key=lambda t: t["name"]):
                            test_name = test["name"]
                            
                            # 対応するファイルとメソッドを取得
                            file_info = test_file_method_map.get(test_name, {"file": "不明", "method": "不明", "function": test["description"]})
                            
                            f.write(f"{test_name:<25}{file_info['file']:<35}{file_info['method']:<30}{file_info['function']}\n")
                        
                        f.write("\n")
                
                # 失敗したテストの詳細セクション
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "テスト結果詳細 - 失敗したテスト\n")
                f.write("=" * 80 + "\n\n")
                
                has_failed_tests = False
                # グループごとに失敗したテストを表示
                for group_idx, (group_name, tests) in enumerate(sorted(grouped_results.items()), 1):
                    # 失敗したテストを抽出
                    failed_tests_list = [test for test in tests if not test["passed"]]
                    
                    if failed_tests_list:
                        has_failed_tests = True
                        f.write(f"{group_idx}. {group_name} (tests/results/{group_name.lower().replace(' ', '_')}_test_results.json)\n")
                        f.write("-" * 80 + "\n")
                        f.write(f"失敗テスト数: {len(failed_tests_list)}/{len(tests)}\n\n")
                        
                        # テーブルヘッダー
                        f.write(f"{'テスト名':<25}{'エラー内容':<35}{'修正案'}\n")
                        f.write("-" * 80 + "\n")
                        
                        for test in sorted(failed_tests_list, key=lambda t: t["name"]):
                            test_name = test["name"]
                            error_message = test.get("error_message", "不明なエラー")
                            fix_suggestion = test.get("fix_suggestion", "")
                            
                            f.write(f"{test_name:<25}{error_message:<35}{fix_suggestion}\n")
                        
                        f.write("\n")
                
                if not has_failed_tests:
                    f.write("すべてのテストは成功しました。\n\n")
                
                # エラーの種類別分析
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "エラーパターン分析\n")
                f.write("=" * 80 + "\n\n")
                
                # エラーメッセージでグループ化
                error_patterns = {}
                for test_key, data in results.items():
                    if not data.get("passed", False):
                        error_msg = data.get("error_message", "不明なエラー")
                        # シンプルなパターンに変換（例: AttributeError, NoSuchElementException）
                        if "AttributeError" in error_msg:
                            pattern = "AttributeError"
                        elif "NoSuchElementException" in error_msg:
                            pattern = "NoSuchElementException"
                        elif "AssertionError" in error_msg:
                            pattern = "AssertionError"
                        else:
                            pattern = "その他のエラー"
                            
                        if pattern not in error_patterns:
                            error_patterns[pattern] = []
                        
                        parts = test_key.split("::")
                        test_name = parts[-1]
                        
                        if len(parts) > 1:
                            group_name = parts[0].replace("_test_results", "").replace("_", " ")
                            display_name = f"{group_name} > {test_name}"
                        else:
                            display_name = test_name
                            
                        error_patterns[pattern].append({
                            "name": display_name,
                            "message": error_msg,
                            "fix": data.get("fix_suggestion", "")
                        })
                
                # エラーパターン別に表示
                if error_patterns:
                    for pattern, errors in sorted(error_patterns.items()):
                        f.write(f"■ {pattern} ({len(errors)}件)\n")
                        f.write("-" * 80 + "\n")
                        
                        # 最初の5件だけ表示
                        for i, error in enumerate(errors[:5]):
                            f.write(f"{i+1}. {error['name']}: {error['message']}\n")
                            if error['fix']:
                                f.write(f"   修正案: {error['fix']}\n")
                        
                        # 5件以上ある場合は省略
                        if len(errors) > 5:
                            f.write(f"... 他 {len(errors) - 5} 件\n")
                        
                        f.write("\n")
                else:
                    f.write("エラーは発生していません。\n\n")
                
                # 修正内容（例：ヘッドレスモード関連）
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "ヘッドレスモード関連の修正内容\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("対象ファイル: tests/test_login_analyzer.py\n")
                f.write("修正内容: ブラウザインスタンス初期化時のheadless設定を修正\n\n")
                
                f.write("修正前:\n")
                f.write("```python\n")
                f.write("headless = env.get_config_value(\"BROWSER\", \"headless\", \"false\")\n")
                f.write("```\n\n")
                
                f.write("修正後:\n")
                f.write("```python\n")
                f.write("headless_config = env.get_config_value(\"BROWSER\", \"headless\", \"false\")\n")
                f.write("headless = headless_config if isinstance(headless_config, bool) else headless_config.lower() == \"true\"\n")
                f.write("```\n\n")
                
                f.write("解決したエラー: Boolean型とString型の互換性問題によるAttributeError\n")
                f.write("効果: 設定がString型で\"true\"や\"false\"の場合も、Boolean型で\"True\"や\"False\"の場合も正しく処理できるようになった\n\n")
                
                # 今後の改善点
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "今後の改善点\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("1. テスト失敗時のスクリーンショット保存機能の強化\n")
                f.write("2. WebDriverManagerのバージョン互換性確保\n")
                f.write("3. 設定値の型変換処理の共通化\n")
                f.write("4. エラーメッセージ検出ロジックの精度向上\n")
                f.write("5. ログファイル出力フォーマットの標準化\n")
                f.write("6. BigQueryテスト用のモックデータセット作成\n")
                f.write("7. テスト前提条件チェックの追加\n")
            
            logger.info(f"詳細テスト結果サマリーを {output_path} に保存しました")
            return output_path
                
        except Exception as e:
            logger.error(f"詳細テスト結果の保存に失敗しました: {e}")
            return None

# モジュールとして実行された場合のメイン処理
def main():
    """コマンドライン実行時のメイン処理"""
    print("Test Result Summary Generator")
    print("-" * 40)
    
    generator = TestSummaryGenerator()
    
    # コマンドライン引数のチェック
    if len(sys.argv) > 1 and sys.argv[1] == '--detailed':
        # 詳細サマリーを生成
        output_path = generator.detailed_summary()
        if output_path:
            print(f"\n詳細テスト結果サマリーを {output_path} に保存しました")
        else:
            print("\nテスト結果が見つからないか、読み込めませんでした。")
            print("まずテストを実行してから再試行してください。")
            return 1
    else:
        # 標準サマリーを生成
        if not generator.generate_summary():
            print("\nNo test results found or could not read them.")
            print("Please run tests first and try again.")
            return 1
            
        # テキスト形式でサマリーをエクスポート
        output_path = generator.export_summary(format="txt")
        if output_path:
            print(f"\nTest result summary saved to {output_path}")
        
    return 0

# バッチファイルから直接実行された場合のエントリーポイント
def run_module():
    """バッチファイルから実行された場合のエントリーポイント"""
    return main()

# スクリプトとして直接実行された場合
if __name__ == "__main__":
    sys.exit(main()) 