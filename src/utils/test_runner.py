#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト実行支援ユーティリティ

テストの並列実行やレポート生成を行います。
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# プロジェクトルートの特定
project_root = Path(__file__).parents[2]

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_env():
    """環境変数などの設定を行う"""
    # 仮想環境のパスを特定
    if sys.platform.startswith('win'):
        venv_python = os.path.join(project_root, "venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(project_root, "venv", "bin", "python")
    
    # 仮想環境のPythonが存在するか確認
    if not os.path.exists(venv_python):
        logger.error(f"仮想環境のPythonが見つかりません: {venv_python}")
        sys.exit(1)
    
    return venv_python

def run_tests(test_path=None, parallel=True, processes=2, verbose=True, report=True, html_report=False, no_skip=False, run_xfail=False):
    """
    テストを実行する
    
    Args:
        test_path (str, optional): テストファイルまたはディレクトリのパス
        parallel (bool): 並列実行するかどうか
        processes (int): 並列プロセス数（auto または 数値）
        verbose (bool): 詳細出力モード
        report (bool): テスト結果レポートを生成するかどうか
        html_report (bool): HTML形式のレポートを生成するかどうか
        no_skip (bool): スキップマーク付きのテストも実行するかどうか
        run_xfail (bool): 失敗が予期されるテストも実行するかどうか
    
    Returns:
        int: 終了コード
    """
    venv_python = setup_env()
    
    # デフォルトのテストパス
    if test_path is None:
        test_path = os.path.join(project_root, "tests")
    
    # pytestのコマンドライン引数を構築
    pytest_args = [venv_python, "-m", "pytest"]
    
    # テストパスを追加
    pytest_args.append(test_path)
    
    # 詳細モード
    if verbose:
        pytest_args.append("-v")
    
    # 並列実行モード
    if parallel:
        if isinstance(processes, int):
            pytest_args.extend(["-n", str(processes)])
        elif processes == "auto":
            pytest_args.extend(["-n", "auto"])
        else:
            pytest_args.extend(["-n", "2"])  # デフォルトは2プロセス
    
    # エラーが発生しても続行
    pytest_args.append("--continue-on-collection-errors")
    
    # トレースバックを短くする
    pytest_args.append("--tb=short")
    
    # スキップマークを無視する
    if no_skip:
        # PytestSkipWarningの代わりに、単純に--skipオプションを無効化
        pytest_args.append("--override-ini=skip=false")
    
    # 失敗が予期されるテストも実行する
    if run_xfail:
        pytest_args.append("--runxfail")
    
    # HTMLレポート生成が有効な場合
    if html_report:
        # HTMLレポートを生成
        report_dir = os.path.join(project_root, "tests", "results", "html")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        pytest_args.extend(["--html", report_file, "--self-contained-html"])
    
    # JSON形式の結果ファイルを生成
    results_dir = os.path.join(project_root, "tests", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # コマンドをログに出力
    logger.info(f"実行コマンド: {' '.join(pytest_args)}")
    
    # サブプロセスとして実行
    try:
        start_time = datetime.now()
        logger.info(f"テスト開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        result = subprocess.run(pytest_args, check=False)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"テスト終了: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"実行時間: {duration:.2f}秒")
        
        # 終了コードに基づいて結果を出力
        if result.returncode == 0:
            logger.info("テスト成功: すべてのテストが通過しました")
        else:
            logger.warning(f"テスト失敗: 終了コード {result.returncode}")
        
        # レポート生成が有効な場合
        if report:
            try:
                # テスト結果サマリーを生成
                from src.utils.test_summary import TestSummaryGenerator
                generator = TestSummaryGenerator()
                
                # サマリー生成
                generator.generate_summary()
                
                # テキストファイルにエクスポート
                date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                summary_path = os.path.join(results_dir, f"テスト結果サマリー_{date_str}.txt")
                generator.export_summary(output_path=Path(summary_path), format="txt")
                logger.info(f"テスト結果サマリー(テキスト形式)を生成しました: {summary_path}")
                
                # JSONファイルにもエクスポート
                json_path = os.path.join(results_dir, f"test_summary_{date_str}.json")
                generator.export_summary(output_path=Path(json_path), format="json")
                logger.info(f"テスト結果サマリー(JSON形式)を生成しました: {json_path}")
            except Exception as e:
                logger.error(f"レポート生成中にエラーが発生しました: {str(e)}")
        
        # HTMLレポートが生成された場合
        if html_report and result.returncode == 0:
            logger.info(f"HTMLレポートが生成されました: {report_file}")
        
        return result.returncode
        
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        return 1

def main():
    """コマンドラインからの実行用エントリーポイント"""
    parser = argparse.ArgumentParser(description="テスト実行ツール")
    parser.add_argument("path", nargs="?", default=None, help="テストファイルまたはディレクトリのパス")
    parser.add_argument("-p", "--parallel", action="store_true", help="並列実行モード")
    parser.add_argument("-n", "--processes", default="auto", help="並列プロセス数（auto または 数値）")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細出力モード")
    parser.add_argument("-r", "--report", action="store_true", help="テスト結果レポートを生成")
    parser.add_argument("--html", action="store_true", help="HTML形式のレポートを生成")
    parser.add_argument("--no-skip", action="store_true", help="スキップマーク付きのテストも実行する")
    parser.add_argument("--run-xfail", action="store_true", help="失敗が予期されるテストも実行する")
    
    args = parser.parse_args()
    
    # プロセス数の処理
    if args.processes != "auto":
        try:
            args.processes = int(args.processes)
        except ValueError:
            logger.warning(f"無効なプロセス数: {args.processes} - 'auto'を使用します")
            args.processes = "auto"
    
    # テスト実行
    exit_code = run_tests(
        test_path=args.path,
        parallel=args.parallel,
        processes=args.processes,
        verbose=args.verbose,
        report=args.report,
        html_report=args.html,
        no_skip=args.no_skip,
        run_xfail=args.run_xfail
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 