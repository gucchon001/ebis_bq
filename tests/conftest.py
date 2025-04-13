# tests/conftest.py

import os
import sys
import pytest
import json
from pathlib import Path
import time
import locale
import datetime
import traceback
from src.utils.environment import env
from src.utils.logging_config import get_logger, setup_logging

# プロジェクトルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# src ディレクトリをPYTHONPATHに追加
src_path = project_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 便宜上、テスト用に環境変数を設定
os.environ["APP_ENV"] = os.environ.get("APP_ENV", "development")

# エンコーディングを修正して文字化けを防ぐ
if sys.platform.startswith('win'):
    # Windows環境での文字化け対策
    import io
    import codecs
    
    # ロケール設定を明示的にUTF-8に変更
    locale.setlocale(locale.LC_ALL, 'Japanese_Japan.utf8')
    
    # 標準出力/標準エラーのエンコーディングを設定
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'backslashreplace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'backslashreplace')
        
    # コンソールのコードページを変更 (CP65001 = UTF-8)
    os.system('chcp 65001 > NUL')

# ロギング設定を初期化
setup_logging(level='DEBUG')
logger = get_logger(__name__)

# テスト用のフィクスチャとして env を提供
@pytest.fixture(scope="session")
def environment():
    """環境設定を提供するフィクスチャ"""
    from src.utils.environment import env
    return env

def pytest_configure(config):
    """pytestの設定を行う"""
    # 環境変数を読み込む
    env.load_env()
    
    # 並列実行設定を設定
    config.option.numprocesses = 'auto'
    config.option.dist = 'loadfile'
    
    logger.info("テスト環境を初期化しました")
    
    # 必要なディレクトリの作成
    os.makedirs("logs", exist_ok=True)
    os.makedirs("tests/results", exist_ok=True)
    
    # ブラウザのヘッドレスモード設定をログ出力
    headless = env.get_config_value("BROWSER", "headless", "false")
    logger.info(f"ブラウザのヘッドレスモード: {headless}")
    
    # テスト実行時間の計測開始
    start_time = time.time()
    config._start_time = start_time
    logger.info(f"テスト実行開始: {time.strftime('%Y-%m-%d %H:%M:%S')}")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """各テストの実行結果を詳細に記録するフック"""
    outcome = yield
    report = outcome.get_result()
    
    # テスト実行データの初期化
    if not hasattr(item, 'test_data'):
        item.test_data = {}
    
    # テスト開始時間
    if report.when == 'call':
        # 実行日時を保存
        exec_time = datetime.datetime.now()
        item.test_data['execution_timestamp'] = exec_time.strftime("%Y-%m-%d %H:%M:%S")
        # 実行時間（秒）も保存
        item.test_data['duration'] = report.duration
    
    # エラーがあった場合に詳細を記録
    if report.outcome != 'passed':
        # エラー情報があれば記録
        if hasattr(report, 'longrepr'):
            if hasattr(call, 'excinfo') and call.excinfo is not None:
                item.test_data['error_type'] = call.excinfo.typename
                item.test_data['error_message'] = str(call.excinfo.value)
                item.test_data['error_traceback'] = ''.join(traceback.format_tb(call.excinfo.tb))
            else:
                # 例外情報がない場合（スキップなど）
                item.test_data['error_message'] = str(report.longrepr)

def pytest_sessionfinish(session, exitstatus):
    """
    セッション終了時にJSONレポートを生成する
    """
    results_dir = Path(project_root) / "tests" / "results"
    os.makedirs(results_dir, exist_ok=True)
    
    # モジュールごとのテスト結果を収集
    module_results = {}
    
    for item in session.items:
        # モジュール名を取得（例: test_file.common.test_access → common_access）
        module_name = item.module.__name__
        module_parts = module_name.split('.')
        
        # 新しいフォルダ構成に対応
        if len(module_parts) >= 3 and module_parts[0] == "test_file":
            # カテゴリとテスト名を取得
            category = module_parts[1]
            test_file = module_parts[2].replace("test_", "")
            # フォルダ名とテスト名を組み合わせたキーを作成（例: common_access）
            module_file = f"{category}_{test_file}"
        else:
            # 従来の取得方法をフォールバックとして残す
            module_file = module_name.split('.')[-1]
        
        # モジュールごとの結果辞書を初期化
        if module_file not in module_results:
            module_results[module_file] = {
                'test_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': category if 'category' in locals() else "その他"
            }
        
        # テスト名を取得
        test_name = item.name
        
        # このテストの結果を取得
        passed = True
        description = "テスト説明が設定されていません"
        execution_time = 0.0
        execution_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_log = None
        
        # Docstring から説明を取得
        if item.function.__doc__:
            description = item.function.__doc__.strip()
        
        # テストデータから情報を取得（開始時間、期間、エラーなど）
        if hasattr(item, 'test_data'):
            data = item.test_data
            if 'duration' in data:
                execution_time = data['duration']
            if 'execution_timestamp' in data:
                execution_timestamp = data['execution_timestamp']
            if 'error_message' in data:
                passed = False
                error_type = data.get('error_type', 'Error')
                error_message = data.get('error_message', 'Unknown error')
                error_traceback = data.get('error_traceback', '')
                error_log = {
                    'type': error_type,
                    'message': error_message,
                    'traceback': error_traceback
                }
        
        # テスト結果を保存
        module_results[module_file][test_name] = {
            'passed': passed,
            'description': description,
            'execution_time': execution_time,
            'execution_timestamp': execution_timestamp,
            'error_log': error_log
        }
    
    # モジュールごとにJSON出力
    for module_name, results in module_results.items():
        output_file = results_dir / f"{module_name}_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"テスト結果をJSONファイルに出力しました: {output_file}")

def pytest_unconfigure(config):
    """テスト終了時の処理"""
    # テスト実行時間の計測終了
    if hasattr(config, '_start_time'):
        end_time = time.time()
        duration = end_time - config._start_time
        logger.info(f"テスト実行終了: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"テスト総実行時間: {duration:.2f}秒")
