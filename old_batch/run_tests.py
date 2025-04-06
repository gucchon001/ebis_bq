#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト実行支援スクリプト

実行方法:
    python run_tests.py

対話形式でテスト実行モードを選択し、テストを実行します。
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python():
    """Pythonが利用可能か確認"""
    try:
        subprocess.run(["python", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: Python not found.")
        print("Please make sure Python is installed.")
        return False


def setup_virtual_env():
    """仮想環境のセットアップ"""
    venv_dir = Path("venv")
    
    if not venv_dir.exists():
        print("Virtual environment not found. Creating new one...")
        try:
            subprocess.run(["python", "-m", "venv", "venv"], check=True)
            print("Virtual environment created.")
        except subprocess.SubprocessError:
            print("Failed to create virtual environment.")
            return False
    
    # 仮想環境のアクティベート（直接実行ではなく環境変数を設定）
    if sys.platform.startswith('win'):
        venv_python = os.path.join("venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join("venv", "bin", "python")
    
    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment Python not found at {venv_python}")
        return False
        
    print("Virtual environment activated.")
    return venv_python


def install_dependencies(venv_python):
    """必要なパッケージのインストール"""
    try:
        # pytestがインストールされているか確認
        result = subprocess.run(
            [venv_python, "-c", "import pytest"], 
            stderr=subprocess.PIPE, 
            stdout=subprocess.PIPE
        )
        
        if result.returncode != 0:
            print("pytest is not installed. Installing...")
            subprocess.run([venv_python, "-m", "pip", "install", "pytest", "pytest-html"], check=True)
    except subprocess.SubprocessError:
        print("Failed to install pytest.")
        return False
    
    return True


def create_results_dir():
    """結果ディレクトリの作成"""
    result_dir = Path("tests") / "results"
    if not result_dir.exists():
        result_dir.mkdir(parents=True)
    return True


def run_all_tests(venv_python):
    """すべてのテストを実行"""
    print("\nRunning all tests...\n")
    subprocess.run([venv_python, "-m", "src.utils.test_runner", "tests", "-v", "--report"])
    
    print("\nTest completed. Some tests might have been skipped due to errors.")
    print("Test results are stored in the tests\\results folder.\n")
    
    show_summary = input("Show test result summary? (Y/N): ")
    if show_summary.upper() == "Y":
        show_test_summary(venv_python)


def run_all_tests_including_skipped(venv_python):
    """スキップマークを無視してすべてのテストを実行"""
    print("\nRunning all tests ignoring skip marks...\n")
    subprocess.run([venv_python, "-m", "src.utils.test_runner", "tests", "-v", "--report", "--no-skip", "--run-xfail"])
    
    print("\nAll tests (including skipped tests) completed.")
    print("Test results are stored in the tests\\results folder.\n")
    
    show_summary = input("Show test result summary? (Y/N): ")
    if show_summary.upper() == "Y":
        show_test_summary(venv_python)


def run_individual_test(venv_python):
    """個別のテストを実行"""
    print("\nEnter the test path to run (e.g. tests/test_module.py::TestClass::test_method):")
    test_path = input("Test path: ")
    
    if test_path:
        subprocess.run([venv_python, "-m", "src.utils.test_runner", test_path, "-v", "--report"])
        
        print("\nIndividual test completed.")
        print("Test results are stored in the tests\\results folder.\n")
    else:
        print("No test path provided. Returning to menu.")


def show_test_summary(venv_python):
    """テスト結果サマリーを表示"""
    print("\nGenerating test result summary...\n")
    subprocess.run([venv_python, "-m", "src.utils.test_summary"])
    input("\nPress Enter to return to the menu...")


def export_test_report(venv_python):
    """テスト結果レポートをエクスポート"""
    print("\nGenerating test result report...\n")
    
    print("Select output format:")
    print("1: Text format (TXT)")
    print("2: JSON format")
    print("3: Both")
    print("4: Back")
    
    format_choice = input("\nSelection (1-4): ")
    
    if format_choice == "1":
        subprocess.run([
            venv_python, "-c", 
            "from src.utils.test_summary import TestSummaryGenerator; "
            "generator = TestSummaryGenerator(); "
            "path = generator.export_summary(format='txt'); "
            "print('Test results saved to ' + str(path))"
        ])
    elif format_choice == "2":
        subprocess.run([
            venv_python, "-c", 
            "from src.utils.test_summary import TestSummaryGenerator; "
            "generator = TestSummaryGenerator(); "
            "path = generator.export_summary(format='json'); "
            "print('Test results saved to ' + str(path))"
        ])
    elif format_choice == "3":
        subprocess.run([
            venv_python, "-c", 
            "from src.utils.test_summary import TestSummaryGenerator; "
            "generator = TestSummaryGenerator(); "
            "path1 = generator.export_summary(format='txt'); "
            "path2 = generator.export_summary(format='json'); "
            "print('Test results saved to ' + str(path1) + ' and ' + str(path2))"
        ])
    elif format_choice == "4":
        return
    else:
        print("Invalid selection. Please try again.")
        export_test_report(venv_python)


def show_menu(venv_python):
    """メインメニューの表示と選択"""
    while True:
        print("\nPlease select execution mode:")
        print("1: Run all tests")
        print("2: Run all tests including skipped tests")
        print("3: Run individual test")
        print("4: Show test result summary")
        print("5: Export test report")
        print("6: Exit")
        
        mode = input("\nSelection (1-6): ")
        
        if mode == "1":
            run_all_tests(venv_python)
        elif mode == "2":
            run_all_tests_including_skipped(venv_python)
        elif mode == "3":
            run_individual_test(venv_python)
        elif mode == "4":
            show_test_summary(venv_python)
        elif mode == "5":
            export_test_report(venv_python)
        elif mode == "6":
            print("\nExiting test runner...")
            break
        else:
            print("Invalid selection. Please try again.")


def main():
    """メイン処理"""
    print("===== Test Execution Tool =====\n")
    
    # Pythonが利用可能か確認
    if not check_python():
        return 1
    
    # 仮想環境のセットアップ
    venv_python = setup_virtual_env()
    if not venv_python:
        return 1
    
    # 依存関係のインストール
    if not install_dependencies(venv_python):
        return 1
    
    # 結果ディレクトリの作成
    create_results_dir()
    
    # メニュー表示
    show_menu(venv_python)
    
    print("\nProcess completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 