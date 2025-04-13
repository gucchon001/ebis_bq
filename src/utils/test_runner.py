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
import json

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
    
    # 結果ディレクトリを確実に作成
    results_dir = os.path.join(project_root, "tests", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # コマンドをログに出力
    logger.info(f"実行コマンド: {' '.join(pytest_args)}")
    
    # サブプロセスとして実行
    try:
        start_time = datetime.now()
        logger.info(f"テスト開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # カスタム環境変数を追加して、レポート生成を有効にする
        env_vars = os.environ.copy()
        if report:
            env_vars["GENERATE_TEST_REPORTS"] = "true"
        
        result = subprocess.run(pytest_args, check=False, env=env_vars)
        
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
                # レポート生成はtest_summary.pyに委譲
                logger.info("test_summary.pyを使用してレポートを生成します...")
                
                # レポート生成を実行（中間ファイルの削除は行わない）
                summary_result = subprocess.run(
                    [venv_python, "-m", "src.utils.test_summary", "--generate-reports", "--no-cleanup"],
                    check=False
                )
                
                if summary_result.returncode == 0:
                    logger.info("レポート生成が完了しました")
                    
                    # レポート生成が完全に終了してから中間ファイルをクリーンアップ
                    logger.info("中間ファイルのクリーンアップを開始します...")
                    cleanup_result = subprocess.run(
                        [venv_python, "-m", "src.utils.test_summary", "--cleanup"],
                        check=False
                    )
                    
                    if cleanup_result.returncode == 0:
                        logger.info("中間ファイルのクリーンアップが完了しました")
                    else:
                        logger.warning(f"中間ファイルのクリーンアップに失敗しました: 終了コード {cleanup_result.returncode}")
                else:
                    logger.warning(f"レポート生成に失敗しました: 終了コード {summary_result.returncode}")
                    logger.warning("中間ファイルは保持されます")
                
            except Exception as e:
                logger.error(f"レポート生成中にエラーが発生しました: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                logger.warning("中間ファイルは保持されます")
        
        # HTMLレポートが生成された場合
        if html_report and result.returncode == 0:
            logger.info(f"HTMLレポートが生成されました: {report_file}")
        
        return result.returncode
        
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
    parser.add_argument("-i", "--interactive", action="store_true", help="インタラクティブモードで実行")
    
    args = parser.parse_args()
    
    # インタラクティブモードの場合
    if args.interactive:
        logger.info("インタラクティブモードはrun_tests.ps1から起動してください")
        print("インタラクティブモードはrun_tests.ps1から起動してください")
        return 0
    
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
    
    return exit_code

def interactive_menu():
    """インタラクティブなテスト実行メニューを表示する（簡略版）"""
    print("\nインタラクティブモードはrun_tests.ps1から起動することを推奨します")
    print("実行を継続する場合は、以下のオプションから選択してください：")
    
    while True:
        print("\n===== テスト実行メニュー (簡略版) =====")
        print("1: すべてのテストを実行")
        print("0: 終了")
        
        choice = input("\n選択してください (0-1): ")
        
        if choice == "0":
            print("プログラムを終了します")
            return
        
        elif choice == "1":
            # すべてのテストを実行
            print("\nすべてのテストを実行します...")
            run_tests(parallel=True, report=True)
        
        else:
            print("無効な選択です。もう一度お試しください。")

if __name__ == "__main__":
    main() 