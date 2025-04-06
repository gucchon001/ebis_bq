#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
実際の接続テストを簡単に実行するためのヘルパースクリプト

使用方法:
    python run_real_tests.py [--skip-openai] [--test-path PATH] [--test-name TEST_NAME]

オプション:
    --skip-openai     OpenAI APIテストをスキップする
    --test-path PATH  テスト対象のGitリポジトリパス（デフォルト: カレントディレクトリ）
    --test-name NAME  特定のテスト名を指定して実行する。指定しない場合はすべてのテストを実行
                      例: test_git_status_on_real_repo

このスクリプトは環境変数を設定し、指定されたテストを実行します。
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="実際の接続テストを実行します")
    parser.add_argument("--skip-openai", action="store_true", help="OpenAI APIテストをスキップ")
    parser.add_argument("--test-path", default=".", help="テスト対象のGitリポジトリパス")
    parser.add_argument("--test-name", help="実行する特定のテスト名")
    parser.add_argument("--api-key", help="OpenAI APIキー (環境変数OPENAI_API_KEYが設定されていない場合に使用)")
    args = parser.parse_args()

    # 現在のディレクトリを取得
    script_dir = Path(__file__).resolve().parent
    
    # testsディレクトリへのパスを作成
    tests_dir = script_dir / "tests"
    
    # テストファイルパスの作成
    test_file = tests_dir / "test_real_integration.py"
    
    if not test_file.exists():
        print(f"エラー: テストファイルが見つかりません: {test_file}")
        sys.exit(1)
    
    # 環境変数の設定
    os.environ["TEST_REPO_PATH"] = str(Path(args.test_path).resolve())
    os.environ["SKIP_OPENAI_TESTS"] = "true" if args.skip_openai else "false"
    
    # APIキーが指定されていて、まだ環境変数が設定されていない場合
    if args.api_key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    # 実行コマンドの構築
    command = ["python", "-m", "pytest", str(test_file), "-v"]
    
    # 特定のテストが指定されている場合
    if args.test_name:
        command[-2] = f"{test_file}::TestRealIntegration::{args.test_name}"
    
    # テスト実行前の情報表示
    print("\n=== 接続テスト実行 ===")
    print(f"テスト対象リポジトリ: {os.environ['TEST_REPO_PATH']}")
    print(f"OpenAIテスト: {'スキップ' if args.skip_openai else '実行'}")
    if args.test_name:
        print(f"テスト名: {args.test_name}")
    else:
        print("すべてのテストを実行します")
    print("====================\n")
    
    try:
        # コマンド実行
        print(f"実行コマンド: {' '.join(command)}")
        result = subprocess.run(command, cwd=script_dir)
        
        # 終了コードに基づいて結果を表示
        if result.returncode == 0:
            print("\n✅ テストが正常に完了しました")
        else:
            print(f"\n❌ テストが失敗しました（終了コード: {result.returncode}）")
        
        sys.exit(result.returncode)
    
    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 