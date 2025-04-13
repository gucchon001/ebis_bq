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
        
    def get_test_results(self):
        """
        テスト結果ファイルを読み込んで解析し、結果を返す
        
        Returns:
            Dict[str, Any]: テスト結果の辞書（キー: テスト名、値: テスト結果）
        """
        results_dir = self.project_root / "tests" / "results"
        
        # 結果ディレクトリが存在しない場合は空の辞書を返す
        if not results_dir.exists():
            logger.warning(f"結果ディレクトリが存在しません: {results_dir}")
            return {}
        
        # test_*_results.json パターンのファイルを検索
        result_pattern1 = "test_*_results.json"
        result_pattern2 = "*_test_results.json"
        result_pattern3 = "test_results_*.json"
        
        test_results = {}
        total_files = 0
        
        # パターン1: test_*_results.json（新しい命名規則）
        for result_file in results_dir.glob(result_pattern1):
            # レポートフォルダ内のファイルは除外
            if "report_" in str(result_file.parent.name):
                continue
                
            try:
                logger.debug(f"テスト結果ファイルを読み込み中: {result_file}")
                
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 結果を統合
                if "results" in data and isinstance(data["results"], dict):
                    # 新しい形式: results フィールドに全テスト結果が格納されている
                    for test_name, test_data in data["results"].items():
                        # カテゴリとパス情報を追加
                        if isinstance(test_data, dict):
                            if "category" not in test_data:
                                test_data["category"] = data.get("category", "その他")
                            if "source_file" not in test_data:
                                test_data["source_file"] = data.get("test_file", "不明").replace("tests/test_file/", "src/").replace("test_", "")
                            if "method" not in test_data:
                                test_data["method"] = test_name
                        test_results[test_name] = test_data
                
                total_files += 1
                        
            except Exception as e:
                logger.error(f"テスト結果ファイルの読み込みに失敗しました: {result_file} - {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"{total_files}個のテスト結果ファイルから{len(test_results)}個のテスト結果を読み込みました")
        return test_results
    
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
            
        passed_count = 0
        total = len(results)
        
        for test_key, data in results.items():
            if isinstance(data, dict):
                if data.get("passed", False):
                    passed_count += 1
            elif isinstance(data, bool):
                # Booleanの場合は直接判定
                if data:
                    passed_count += 1
            elif isinstance(data, (int, float)):
                # 数値の場合は0以外をPASSとして扱う
                if data:
                    passed_count += 1
            # その他の型は失敗として扱う
        
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
            # データが辞書でない場合の対応
            if not isinstance(data, dict):
                logger.warning(f"テスト結果が不正な形式です: {test_key} => {data}")
                if isinstance(data, bool):
                    status = "PASS" if data else "FAIL"
                    description = "No description available"
                elif isinstance(data, (int, float)):
                    status = "PASS" if data else "FAIL"
                    description = "No description available"
                else:
                    status = "ERROR"
                    description = f"Invalid data type: {type(data)}"
            else:
                status = "PASS" if data.get("passed", False) else "FAIL"
                description = data.get("description", "No description")
            
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
                
            print(f"{display_name:<60}{status:<10}{description}")
            
            if status == "PASS":
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
                output_path = self.project_root / "tests" / "results" / f"test_summary_{date_str}.json"
            else:
                output_path = self.project_root / "tests" / "results" / f"テスト結果サマリー_{date_str}.txt"
        
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
                    f.write(" " * 25 + "テスト実行結果サマリー (" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
                    f.write("=" * 80 + "\n\n")
                    
                    f.write(f"{'TEST NAME':<60}{'RESULT':<10}{'FUNCTIONALITY ASSURED'}\n")
                    f.write("-" * 100 + "\n")
                    
                    for test_key, data in sorted(results.items()):
                        # データの型に応じた処理
                        if isinstance(data, dict):
                            status = "PASS" if data.get("passed", False) else "FAIL"
                            description = data.get("description", "No description")
                        elif isinstance(data, bool):
                            status = "PASS" if data else "FAIL"
                            description = "No description available"
                        elif isinstance(data, (int, float)):
                            status = "PASS" if data else "FAIL"
                            description = "No description available"
                        else:
                            status = "ERROR"
                            description = f"Invalid data type: {type(data)}"
                            
                        parts = test_key.split("::")
                        test_name = parts[-1]
                        
                        if len(parts) > 1:
                            file_name = parts[0].replace("_test_results", "").replace("_", " ")
                            display_name = f"{file_name} > {test_name}"
                        else:
                            display_name = test_name
                            
                        if len(display_name) > 57:
                            display_name = display_name[:54] + "..."
                            
                        f.write(f"{display_name:<60}{status:<10}{description}\n")
                    
                    f.write("-" * 100 + "\n")
                    f.write(f"Total: {stats[0]} tests ({stats[1]} passed / {stats[2]} failed)\n")
                    f.write(f"Success rate: {stats[3]:.1f}%\n")
                    f.write("=" * 80 + "\n")
            
            logger.info(f"テスト結果サマリーを {output_path} に保存しました")
            return output_path
                
        except Exception as e:
            logger.error(f"テスト結果の保存に失敗しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def detailed_summary(self, results: Optional[Dict[str, Any]] = None, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        詳細なテスト結果サマリーを生成する
        
        Args:
            results (Optional[Dict[str, Any]], optional): テスト結果の辞書
            output_path (Optional[Path], optional): 出力先のパス
            
        Returns:
            Optional[Path]: 生成されたファイルのパス
        """
        if results is None:
            results = self.get_test_results()
            
        if not results:
            logger.warning("テスト結果が見つかりません")
            return None
        
        try:
            # 出力パスの設定
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.project_root / "tests" / "results" / f"detailed_results_{timestamp}.txt"
            
            # 結果ディレクトリが存在しない場合は作成
            output_dir = output_path.parent
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
                
            # 統計情報の取得
            stats = self.get_summary_stats(results)
            
            # カテゴリ別にテスト結果をグループ化
            grouped_results = {}
            
            for test_key, data in results.items():
                # テスト結果データの取得
                if isinstance(data, dict):
                    passed = data.get("passed", False)
                    description = data.get("description", "説明なし")
                    source_file = data.get("source_file", "不明")
                    method = data.get("method", "不明")
                    execution_time = data.get("execution_time", 0.0)
                    execution_timestamp = data.get("execution_timestamp", "不明")
                    category = data.get("category", "その他")
                else:
                    passed = data
                    description = "説明なし"
                    source_file = "不明"
                    method = "不明"
                    execution_time = 0.0
                    execution_timestamp = "不明"
                    category = "その他"
                
                # カテゴリごとにグループ化
                if category not in grouped_results:
                    grouped_results[category] = []
                
                grouped_results[category].append({
                    "name": test_key,
                    "passed": passed,
                    "description": description,
                    "source_file": source_file,
                    "method": method,
                    "execution_time": execution_time,
                    "execution_timestamp": execution_timestamp
                })
            
            # レポートの生成
            with open(output_path, "w", encoding="utf-8") as f:
                # ヘッダー
                f.write("=" * 80 + "\n")
                f.write(f"                         テスト実行結果サマリー ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                
                # 環境情報
                f.write("【実行環境情報】" + "=" * 64 + "\n")
                f.write("環境: Windows 10\n")
                f.write("Python: 3.x\n")
                f.write("仮想環境: venv\n")
                f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                
                # 実行状況
                f.write("【テスト実行状況】\n")
                f.write(f"実行テスト数: {stats['total']}件\n")
                f.write(f"成功: {stats['passed']}件\n")
                f.write(f"失敗: {stats['failed']}件\n")
                f.write(f"成功率: {stats['success_rate']:.1f}%\n\n")
                
                f.write(f"合計実行時間: {stats['total_time']:.2f}秒\n")
                f.write(f"平均テスト時間: {stats['avg_time']:.2f}秒\n")
                f.write(f"最長テスト時間: {stats['max_time']:.2f}秒({stats['longest_test']})\n\n")
                
                # 詳細結果
                f.write("=" * 80 + "\n")
                f.write("                         テスト結果詳細 - 成功したテスト\n")
                f.write("=" * 80 + "\n\n")
                
                # グループごとに表示
                for group_idx, (group_name, tests) in enumerate(sorted(grouped_results.items()), 1):
                    # 成功したテストを抽出
                    passed_count = sum(1 for test in tests if test["passed"])
                    
                    # ステータス行
                    f.write(f"{group_idx}. {group_name} (テストカテゴリ: {group_name})\n")
                    f.write("-" * 100 + "\n")
                    f.write(f"ステータス: 成功 ({passed_count}/{len(tests)}テスト成功)\n\n")
                        
                    # テーブルヘッダー
                    f.write(f"{'テスト名':<20}{'対応ファイル':<30}{'メソッド':<20}{'実行時間':<10}{'実行日時':<20}{'検証機能':<50}\n")
                    f.write("-" * 100 + "\n")
                    
                    # 成功したテストのみを表示
                    passed_tests_list = [test for test in tests if test["passed"]]
                    for test in passed_tests_list:
                        f.write(f"{test['name']:<20}{test['source_file']:<30}{test['method']:<20}{test['execution_time']:<10.2f}{test['execution_timestamp']:<20}{test['description']:<50}\n")
                        f.write("\n")
                
                return output_path
                
        except Exception as e:
            logger.error(f"詳細サマリーの生成に失敗しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def create_report_folder_with_reports(self, no_cleanup=False):
        """
        タイムスタンプ付きフォルダを作成し、その中に各種レポートを生成する
        
        Args:
            no_cleanup (bool): Trueの場合、中間ファイルを削除しない
        
        Returns:
            bool: 成功時True、失敗時False
        """
        results = self.get_test_results()
        if not results:
            logger.error("テスト結果が見つかりません")
            return False
        
        try:
            # タイムスタンプの取得
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # レポートフォルダの作成
            report_folder = self.project_root / "tests" / "results" / f"report_{timestamp}"
            report_folder.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"レポートフォルダを作成しました: {report_folder}")
            
            # 統計情報の取得
            stats = self.get_summary_stats(results)
            
            # 1. テスト結果サマリーJSON
            summary_json_path = report_folder / f"test_summary_{timestamp}.json"
            summary_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_tests": stats[0],
                "passed_tests": stats[1],
                "failed_tests": stats[2],
                "pass_rate": stats[3],
                "results": results
            }
            
            with open(summary_json_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            # 2. テスト結果サマリー（テキスト）
            report_summary_path = report_folder / f"テスト結果サマリー_{timestamp}.txt"
            with open(report_summary_path, "w", encoding="utf-8-sig") as f:
                f.write("=" * 80 + "\n")
                f.write(" " * 25 + "テスト実行結果サマリー (" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"{'TEST NAME':<60}{'RESULT':<10}{'FUNCTIONALITY ASSURED'}\n")
                f.write("-" * 100 + "\n")
                
                for test_key, data in sorted(results.items()):
                    # データの型に応じた処理
                    if isinstance(data, dict):
                        status = "PASS" if data.get("passed", False) else "FAIL"
                        description = data.get("description", "No description")
                    elif isinstance(data, bool):
                        status = "PASS" if data else "FAIL"
                        description = "No description available"
                    elif isinstance(data, (int, float)):
                        status = "PASS" if data else "FAIL"
                        description = "No description available"
                    else:
                        status = "ERROR"
                        description = f"Invalid data type: {type(data)}"
                    
                    parts = test_key.split("::")
                    test_name = parts[-1]
                    
                    if len(parts) > 1:
                        file_name = parts[0].replace("_test_results", "").replace("_", " ")
                        display_name = f"{file_name} > {test_name}"
                    else:
                        display_name = test_name
                    
                    if len(display_name) > 57:
                        display_name = display_name[:54] + "..."
                        
                    f.write(f"{display_name:<60}{status:<10}{description}\n")
                
                f.write("-" * 100 + "\n")
                f.write(f"Total: {stats[0]} tests ({stats[1]} passed / {stats[2]} failed)\n")
                f.write(f"Success rate: {stats[3]:.1f}%\n")
                f.write("=" * 80 + "\n")
            
            # 3. 詳細テスト結果
            report_details_path = report_folder / f"詳細テスト結果_{timestamp}.txt"
            self.detailed_summary(output_path=report_details_path)
            
            # 4. 生成されたレポートファイルの一覧
            report_files_path = report_folder / f"生成されたレポートファイル_{timestamp}.txt"
            with open(report_files_path, "w", encoding="utf-8") as f:
                f.write(f"テスト実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("生成されたレポートファイル:\n")
                f.write("1. テスト結果サマリー (JSON形式):\n")
                f.write(f"   {summary_json_path.name}\n\n")
                f.write("2. テスト結果サマリー (テキスト形式):\n")
                f.write(f"   {report_summary_path.name}\n\n")
                f.write("3. 詳細テスト結果 (テキスト形式):\n")
                f.write(f"   {report_details_path.name}\n")
            
            # 5. 中間ファイルを削除（no_cleanupがFalseの場合のみ）
            if not no_cleanup:
                self.cleanup_test_result_files()
            
            logger.info(f"レポートファイルの生成が完了しました:")
            logger.info(f"- {summary_json_path}")
            logger.info(f"- {report_summary_path}")
            logger.info(f"- {report_details_path}")
            logger.info(f"- {report_files_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"レポートフォルダの作成中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def cleanup_test_result_files(self):
        """
        不要なテスト結果ファイルを削除する
        """
        try:
            # *_test_results.jsonファイルを検索して削除
            test_result_patterns = ["*_test_results.json", "test_results_*.json"]
            root_json_patterns = ["test_summary_*.json"]
            root_text_patterns = ["テスト結果サマリー_*.txt", "詳細テスト結果_*.txt", "生成されたレポートファイル_*.txt"]
            
            # 削除対象ファイルのリスト
            files_to_delete = []
            
            # テスト結果JSONファイルを検索
            for pattern in test_result_patterns:
                for file_path in self.results_dir.glob(pattern):
                    files_to_delete.append(file_path)
            
            # ルートディレクトリのJSONファイルを検索
            for pattern in root_json_patterns:
                for file_path in self.results_dir.glob(pattern):
                    # report_*フォルダの中にあるファイルは除外
                    if "report_" not in str(file_path.parent.name):
                        files_to_delete.append(file_path)
            
            # ルートディレクトリのテキストファイルを検索
            for pattern in root_text_patterns:
                for file_path in self.results_dir.glob(pattern):
                    # report_*フォルダの中にあるファイルは除外
                    if "report_" not in str(file_path.parent.name):
                        files_to_delete.append(file_path)
            
            # ファイルを削除
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"ファイルを削除しました: {file_path}")
                except Exception as e:
                    logger.warning(f"ファイル {file_path} の削除に失敗しました: {e}")
            
            if deleted_count > 0:
                logger.info(f"{deleted_count}個の中間ファイルを削除しました")
            
            return deleted_count
        except Exception as e:
            logger.error(f"ファイル削除中にエラーが発生しました: {e}")
            return 0

# モジュールとして実行された場合のメイン処理
def main():
    """コマンドライン実行時のメイン処理"""
    # コマンドライン引数の解析
    import argparse
    parser = argparse.ArgumentParser(description="テスト結果サマリー生成ツール")
    parser.add_argument("--detailed", action="store_true", help="詳細サマリーを生成")
    parser.add_argument("--generate-reports", action="store_true", help="すべてのレポートを生成")
    parser.add_argument("--folder", action="store_true", help="フォルダ内にタイムスタンプ付きでレポート保存")
    parser.add_argument("--output", type=str, help="出力ファイルパス")
    parser.add_argument("--format", choices=["txt", "json", "both"], default="both", help="出力形式")
    parser.add_argument("--cleanup", action="store_true", help="中間ファイルを削除")
    parser.add_argument("--no-cleanup", action="store_true", help="レポート生成時に中間ファイルを削除しない")
    
    args = parser.parse_args()
    
    print("Test Result Summary Generator")
    print("-" * 40)
    
    generator = TestSummaryGenerator()
    
    # 中間ファイルの削除
    if args.cleanup:
        deleted_count = generator.cleanup_test_result_files()
        print(f"{deleted_count}個の中間ファイルを削除しました")
        return 0
    
    # すべてのレポートを生成（test_runner.pyから呼び出される）
    if args.generate_reports:
        # フォルダ構造でレポートを生成（no_cleanupオプションを考慮）
        result = generator.create_report_folder_with_reports(no_cleanup=args.no_cleanup)
        return 0 if result else 1
    
    # 詳細サマリーを生成
    if args.detailed:
        output_path = None
        if args.output:
            output_path = Path(args.output)
        
        # タイムスタンプ付きフォルダに保存
        if args.folder:
            result = generator.create_report_folder_with_reports()
            return 0 if result else 1
        
        # 通常の詳細レポート生成
        output_path = generator.detailed_summary(output_path=output_path)
        if output_path:
            print(f"\n詳細テスト結果サマリーを {output_path} に保存しました")
        else:
            print("\nテスト結果が見つからないか、読み込めませんでした。")
            print("まずテストを実行してから再試行してください。")
            return 1
    else:
        # 標準サマリーを生成して表示
        if not generator.generate_summary():
            print("\nNo test results found or could not read them.")
            print("Please run tests first and try again.")
            return 1
            
        # フォルダモードが指定されていれば、フォルダにレポートを生成
        if args.folder:
            result = generator.create_report_folder_with_reports()
            return 0 if result else 1
        
        # 通常の出力形式
        if args.format in ["txt", "both"]:
            output_path = generator.export_summary(format="txt")
            if output_path:
                print(f"\nTest result summary (TEXT) saved to {output_path}")
        
        if args.format in ["json", "both"]:
            output_path = generator.export_summary(format="json")
            if output_path:
                print(f"\nTest result summary (JSON) saved to {output_path}")
        
    return 0

# スクリプトとして直接実行された場合
if __name__ == "__main__":
    sys.exit(main()) 