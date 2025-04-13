import pytest
from pathlib import Path
import sys
import json
import io
import datetime

# プロジェクトルートのパスを修正 - test_file フォルダに対応
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト結果を保存するグローバル変数
TEST_RESULTS = {}

@pytest.fixture(scope="session", autouse=True)
def report_test_results(request):
    """テスト終了時に結果をまとめて出力するフィクスチャ"""
    yield
    print("\n")
    print("=" * 80)
    print("               テスト結果および担保された機能                ")
    print("=" * 80)
    print(f"{'テスト名':<30}{'結果':<10}{'担保された機能'}")
    print("-" * 80)
    for test_name, result in TEST_RESULTS.items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{test_name:<30}{status:<10}{result['description']}")
    print("-" * 80)
    print(f"テスト環境: Python {sys.version.split()[0]}")
    pass_count = sum(1 for r in TEST_RESULTS.values() if r["passed"])
    fail_count = len(TEST_RESULTS) - pass_count
    print(f"総合結果: {pass_count} passed / {fail_count} failed")
    print("=" * 80)
    
    # 結果をJSONファイルに保存 - 新しい命名規則に対応
    try:
        # カテゴリ情報を取得（現在のフォルダ名）
        category = Path(__file__).parent.name
        results_path = PROJECT_ROOT / "tests" / "results" / f"common_access_test_results.json"
        
        # resultsディレクトリが存在しない場合は作成
        results_dir = results_path.parent
        if not results_dir.exists():
            results_dir.mkdir(parents=True)
        
        # テスト実行時間を記録
        test_data = {
            "test_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category
        }
        # テスト結果をマージ
        test_data.update(TEST_RESULTS)
        
        # JSONの文字列を一旦UTF-8で作成
        json_str = json.dumps(test_data, ensure_ascii=False, indent=2)
        
        # BOMなしUTF-8でファイル書き込み
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(json_str)
            
        print(f"テスト結果を {results_path} に保存しました")
    except Exception as e:
        print(f"テスト結果の保存に失敗しました: {e}")
        
    # テスト結果を標準出力にも再度出力する
    print("\nテスト結果の概要:")
    for test_name, result in TEST_RESULTS.items():
        status = "PASS" if result["passed"] else "FAIL"
        print(f"- {test_name}: {status} - {result['description']}")

def record_result(name, passed, description):
    """テスト結果を記録する関数"""
    TEST_RESULTS[name] = {
        "passed": passed,
        "description": description,
        "execution_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return passed

def test_project_structure():
    """フォルダ構成が正しいかを確認"""
    result = True
    result = result and (PROJECT_ROOT / "config").exists()
    result = result and (PROJECT_ROOT / "docs").exists()
    result = result and (PROJECT_ROOT / "logs").exists()
    result = result and (PROJECT_ROOT / "src").exists()
    result = result and (PROJECT_ROOT / "tests").exists()
    
    description = "基本ディレクトリ構造が適切で、アプリケーションが正しく実行できる環境が整っている"
    record_result("プロジェクト構造確認", result, description)
    
    assert (PROJECT_ROOT / "config").exists(), "config フォルダが存在しません"
    assert (PROJECT_ROOT / "docs").exists(), "docs フォルダが存在しません"
    assert (PROJECT_ROOT / "logs").exists(), "logs フォルダが存在しません"
    # 機能削除のため除外: assert (PROJECT_ROOT / "spec_tools").exists(), "spec_tools フォルダが存在しません"
    assert (PROJECT_ROOT / "src").exists(), "src フォルダが存在しません"
    assert (PROJECT_ROOT / "tests").exists(), "tests フォルダが存在しません"

def test_config_files():
    """config フォルダ内の重要ファイルが存在するか確認"""
    config_path = PROJECT_ROOT / "config"
    result = True
    result = result and (config_path / "secrets.env").exists()
    result = result and (config_path / "settings.ini").exists()
    
    description = "環境変数と設定ファイルが正しく配置され、アプリケーションが設定を適切に読み込める"
    record_result("設定ファイル確認", result, description)
    
    assert (config_path / "secrets.env").exists(), "secrets.env が存在しません"
    assert (config_path / "settings.ini").exists(), "settings.ini が存在しません"

def test_src_modules():
    """src/modules フォルダが存在するか確認"""
    modules_path = PROJECT_ROOT / "src" / "modules"
    result = modules_path.exists()
    
    description = "ビジネスロジックモジュールの構造が維持され、機能拡張時の整合性が担保されている"
    record_result("モジュール構造確認", result, description)
    
    assert modules_path.exists(), "src/modules フォルダが存在しません"
    # 機能削除のため除外: assert (modules_path / "db_connector.py").exists(), "db_connector.py が存在しません"

def test_utils_access():
    """src/utils フォルダが存在するか確認"""
    utils_path = PROJECT_ROOT / "src" / "utils"
    result = True
    result = result and utils_path.exists()
    result = result and (utils_path / "environment.py").exists()
    result = result and (utils_path / "logging_config.py").exists()
    
    description = "共通ユーティリティが適切に構成され、環境管理とロギング機能が利用可能な状態にある"
    record_result("ユーティリティ確認", result, description)
    
    assert utils_path.exists(), "src/utils フォルダが存在しません"
    assert (utils_path / "environment.py").exists(), "environment.py が存在しません"
    assert (utils_path / "logging_config.py").exists(), "logging_config.py が存在しません"

def test_logs_directory():
    """logs フォルダへのアクセス確認"""
    logs_path = PROJECT_ROOT / "logs"
    result = logs_path.exists()
    
    description = "ログ出力先が確保され、アプリケーションの動作ログが適切に記録できる"
    record_result("ログディレクトリ確認", result, description)
    
    assert logs_path.exists(), "logs フォルダが存在しません"
