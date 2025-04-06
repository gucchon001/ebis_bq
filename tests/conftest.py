# tests/conftest.py

import os
import sys
import pytest
from pathlib import Path
import time
import locale
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

def pytest_unconfigure(config):
    """テスト終了時の処理"""
    # テスト実行時間の計測終了
    if hasattr(config, '_start_time'):
        end_time = time.time()
        duration = end_time - config._start_time
        logger.info(f"テスト実行終了: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"テスト総実行時間: {duration:.2f}秒")
