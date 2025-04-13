#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Cloud認証のテスト

サービスアカウントファイルの存在と認証機能、
BigQueryスキーマ取得およびGCSファイル操作をテストします。
"""

import os
import io
import sys
import pytest
import json
import datetime
from pathlib import Path
from datetime import datetime
from google.cloud import bigquery
from google.cloud import storage

# プロジェクトルートを正しく設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# テスト対象のモジュールをインポート
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.bigquery import GoogleCloudAuth
from src.utils.environment import env

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
        results_path = PROJECT_ROOT / "tests" / "results" / f"{category}_google_cloud_auth_test_results.json"
        
        # resultsディレクトリが存在しない場合は作成
        results_dir = results_path.parent
        if not results_dir.exists():
            results_dir.mkdir(parents=True)
        
        # テスト実行時間を記録
        test_data = {
            "test_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        "execution_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return passed

def test_service_account_file_exists():
    """GCPサービスアカウントファイルが存在するかテスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルのパスを取得
    key_path = auth.key_path
    
    # ファイルの存在確認
    if not key_path or not os.path.exists(key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {key_path}")
    
    result = os.path.exists(key_path)
    assert result, f"GCPサービスアカウントファイルが存在しません: {key_path}"
    print(f"GCPサービスアカウントファイルの確認: OK - {key_path}")
    
    return record_result(
        "test_service_account_file_exists",
        result,
        "GCPサービスアカウントファイルの存在確認"
    )

def test_bigquery_auth():
    """BigQueryへの認証テスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # 認証を実行
    client = auth.authenticate_bigquery()
    
    # 認証が成功したか確認
    result = client is not None and isinstance(client, bigquery.Client)
    assert result, "認証に失敗しました"
    
    print(f"BigQuery認証: OK")
    
    return record_result(
        "test_bigquery_auth",
        result,
        "BigQueryへの認証機能"
    )

def test_gcs_auth():
    """GCSへの認証テスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # 認証を実行
    client = auth.authenticate_gcs()
    
    # 認証が成功したか確認
    result = client is not None and isinstance(client, storage.Client)
    assert result, "認証に失敗しました"
    
    print(f"GCS認証: OK")
    
    return record_result(
        "test_gcs_auth",
        result,
        "Google Cloud Storageへの認証機能"
    )

def test_dataset_exists():
    """データセットの存在確認テスト"""
    # 環境変数の読み込み
    env.load_env()
    
    # データセット名を環境変数から取得
    test_dataset = env.get_env_var("BIGQUERY_DATASET")
    if not test_dataset:
        pytest.skip("環境変数 BIGQUERY_DATASET が設定されていません (secrets.env)")
    
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # データセットの存在を確認
    client = auth.authenticate_bigquery()
    if client is None:
        pytest.fail("BigQueryの認証に失敗しました")
    
    exists = auth.dataset_exists(test_dataset)
    
    # データセットが存在しない場合は作成する
    if not exists:
        try:
            # データセットを作成
            dataset_id = f"{auth.project_id}.{test_dataset}"
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"  # ロケーションを設定
            dataset = client.create_dataset(dataset)  # APIリクエストを作成して実行
            print(f"データセット '{test_dataset}' を作成しました")
            exists = True
        except Exception as e:
            pytest.fail(f"データセット '{test_dataset}' の作成に失敗しました: {e}")
    
    result = exists
    assert result, f"データセット '{test_dataset}' が存在しません"
    print(f"データセット '{test_dataset}' の確認: OK")
    
    return record_result(
        "test_dataset_exists",
        result,
        "BigQueryデータセットの存在確認と作成機能"
    )

def test_table_exists():
    """テーブルの存在確認テスト"""
    # 環境変数の読み込み
    env.load_env()
    
    # データセット名とテーブル名を環境変数から取得
    test_dataset = env.get_env_var("BIGQUERY_DATASET")
    test_table = env.get_env_var("BIGQUERY_TABLE", "sample_table")
    
    if not test_dataset:
        pytest.skip("環境変数 BIGQUERY_DATASET が設定されていません (secrets.env)")
    
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # BigQueryクライアント取得
    client = auth.authenticate_bigquery()
    if client is None:
        pytest.fail("BigQueryの認証に失敗しました")
    
    # データセットの存在確認
    dataset_exists = auth.dataset_exists(test_dataset)
    if not dataset_exists:
        pytest.skip(f"テスト用データセット '{test_dataset}' が存在しません。先にtest_dataset_existsを実行してください。")
    
    # テーブルの存在を確認
    exists = auth.table_exists(test_table, test_dataset)
    
    # テーブルが存在しない場合は作成する
    if not exists:
        try:
            # テーブルスキーマを定義
            schema = [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED", description="一意のID"),
                bigquery.SchemaField("name", "STRING", mode="NULLABLE", description="名前"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE", description="作成日時"),
                bigquery.SchemaField("value", "INTEGER", mode="NULLABLE", description="値"),
                bigquery.SchemaField("is_active", "BOOLEAN", mode="NULLABLE", description="アクティブフラグ")
            ]
            
            # テーブルを作成
            table_id = f"{auth.project_id}.{test_dataset}.{test_table}"
            table = bigquery.Table(table_id, schema=schema)
            table = client.create_table(table)
            
            # サンプルデータを挿入
            rows_to_insert = [
                {"id": "1", "name": "テスト1", "created_at": datetime.now().isoformat(), "value": 100, "is_active": True},
                {"id": "2", "name": "テスト2", "created_at": datetime.now().isoformat(), "value": 200, "is_active": False}
            ]
            
            errors = client.insert_rows_json(table, rows_to_insert)
            if errors:
                print(f"サンプルデータの挿入中にエラーが発生しました: {errors}")
            else:
                print(f"テーブル '{test_dataset}.{test_table}' にサンプルデータを挿入しました")
            
            print(f"テーブル '{test_dataset}.{test_table}' を作成しました")
            exists = True
        except Exception as e:
            pytest.fail(f"テーブル '{test_dataset}.{test_table}' の作成に失敗しました: {e}")
    
    result = exists
    assert result, f"テーブル '{test_dataset}.{test_table}' が存在しません"
    print(f"テーブル '{test_dataset}.{test_table}' の確認: OK")
    
    return record_result(
        "test_table_exists",
        result,
        "BigQueryテーブルの存在確認と作成機能"
    )

def test_get_table_schema():
    """テーブルスキーマ取得テスト"""
    # 環境変数の読み込み
    env.load_env()
    
    # データセット名とテーブル名を環境変数から取得
    test_dataset = env.get_env_var("BIGQUERY_DATASET")
    test_table = env.get_env_var("BIGQUERY_TABLE", "sample_table")
    
    if not test_dataset:
        pytest.skip("環境変数 BIGQUERY_DATASET が設定されていません (secrets.env)")
    
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # データセットとテーブルの存在確認
    client = auth.authenticate_bigquery()
    if client is None:
        pytest.fail("BigQueryの認証に失敗しました")
    
    # データセットとテーブルの存在を確認
    dataset_exists = auth.dataset_exists(test_dataset)
    table_exists = auth.table_exists(test_table, test_dataset)
    
    if not dataset_exists:
        pytest.skip(f"テスト用データセット '{test_dataset}' が存在しません。先にtest_dataset_existsを実行してください。")
    
    if not table_exists:
        pytest.skip(f"テスト用テーブル '{test_dataset}.{test_table}' が存在しません。先にtest_table_existsを実行してください。")
    
    # スキーマの取得
    schema = auth.get_table_schema(test_table, test_dataset)
    
    # スキーマが取得できたか確認
    result = schema is not None and len(schema) > 0
    assert result, f"テーブル '{test_dataset}.{test_table}' のスキーマを取得できませんでした"
    
    # 期待されるフィールドが含まれているか確認（最低限のフィールドチェックのみ）
    field_names = [field.name for field in schema]
    assert len(field_names) > 0, "フィールドが存在しません"
    
    # 詳細なスキーマ情報を表示
    print(f"\nテーブルスキーマ ({test_dataset}.{test_table}):")
    for field in schema:
        print(f" - {field.name}: {field.field_type} ({field.mode})")
        
        # ネストされたフィールドがあれば表示
        if field.fields:
            for nested_field in field.fields:
                print(f"   * {nested_field.name}: {nested_field.field_type} ({nested_field.mode})")
    
    print(f"\nテーブルスキーマ取得: OK - {len(schema)}フィールド")
    
    return record_result(
        "test_get_table_schema",
        result,
        "BigQueryテーブルスキーマ取得機能"
    )

def test_bucket_exists():
    """バケットの存在確認テスト"""
    # 環境変数の読み込み
    env.load_env()
    
    # バケット名を環境変数から取得
    test_bucket = env.get_env_var("GCS_BUCKET_NAME")
    if not test_bucket:
        pytest.skip("環境変数 GCS_BUCKET_NAME が設定されていません (secrets.env)")
    
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # バケットの存在を確認
    exists = auth.bucket_exists(test_bucket)
    
    # バケットが存在しない場合は作成する
    if not exists:
        try:
            # バケットを作成
            client = auth.authenticate_gcs()
            if client is None:
                pytest.fail("GCSの認証に失敗しました")
            
            # バケットを作成
            bucket = client.create_bucket(test_bucket)
            print(f"バケット '{test_bucket}' を作成しました")
            exists = True
        except Exception as e:
            pytest.fail(f"バケット '{test_bucket}' の作成に失敗しました: {e}")
    
    result = exists
    assert result, f"バケット '{test_bucket}' が存在しません"
    print(f"バケット '{test_bucket}' の確認: OK")
    
    return record_result(
        "test_bucket_exists",
        result,
        "GCSバケットの存在確認と作成機能"
    )

def test_upload_and_list_file():
    """ファイルのアップロードとリストテスト"""
    # 環境変数の読み込み
    env.load_env()
    
    # バケット名を環境変数から取得
    test_bucket = env.get_env_var("GCS_BUCKET_NAME")
    if not test_bucket:
        pytest.skip("環境変数 GCS_BUCKET_NAME が設定されていません (secrets.env)")
    
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # バケットの存在を確認
    bucket_exists = auth.bucket_exists(test_bucket)
    if not bucket_exists:
        pytest.skip(f"テスト用バケット '{test_bucket}' が存在しません。先にtest_bucket_existsを実行してください。")
    
    # GCSクライアント取得
    client = auth.authenticate_gcs()
    if client is None:
        pytest.fail("GCSの認証に失敗しました")
    
    # バケットを取得
    bucket = client.get_bucket(test_bucket)
    
    # テスト用のデータを作成してアップロード
    test_data = "これはテスト用のデータです。"
    test_blob_name = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    blob = bucket.blob(test_blob_name)
    blob.upload_from_string(test_data, content_type="text/plain")
    
    print(f"テストファイル '{test_blob_name}' をアップロードしました")
    
    # アップロードしたファイルが存在するか確認
    blobs = list(client.list_blobs(test_bucket, prefix="test_file_"))
    
    # ファイルが見つかったか確認
    uploaded_found = any(b.name == test_blob_name for b in blobs)
    result = uploaded_found
    assert result, f"アップロードしたファイル '{test_blob_name}' がバケット '{test_bucket}' に見つかりません"
    
    print(f"バケット '{test_bucket}' のファイル一覧:")
    for blob in blobs:
        print(f" - {blob.name} ({blob.size} bytes) - {blob.updated}")
    
    # アップロード成功
    print(f"ファイルのアップロードとリスト: OK")
    
    return record_result(
        "test_upload_and_list_file",
        result,
        "GCSファイルのアップロードとリスト機能"
    )

if __name__ == "__main__":
    pytest.main(['-v', __file__]) 