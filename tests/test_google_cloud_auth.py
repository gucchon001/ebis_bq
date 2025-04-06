#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Cloud認証のテスト

サービスアカウントファイルの存在と認証機能、
BigQueryスキーマ取得およびGCSファイル操作をテストします。
"""

import os
import io
import pytest
from datetime import datetime
from google.cloud import bigquery
from google.cloud import storage

from src.utils.bigquery import GoogleCloudAuth
from src.utils.environment import env

def test_service_account_file_exists():
    """GCPサービスアカウントファイルが存在するかテスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルのパスを取得
    key_path = auth.key_path
    
    # ファイルの存在確認
    if not key_path or not os.path.exists(key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {key_path}")
    
    assert os.path.exists(key_path), f"GCPサービスアカウントファイルが存在しません: {key_path}"
    print(f"GCPサービスアカウントファイルの確認: OK - {key_path}")

def test_bigquery_auth():
    """BigQueryへの認証テスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # 認証を実行
    client = auth.authenticate_bigquery()
    
    # 認証が成功したか確認
    assert client is not None, "認証に失敗しました"
    assert isinstance(client, bigquery.Client), "認証結果が正しいクライアントインスタンスではありません"
    
    print(f"BigQuery認証: OK")

def test_gcs_auth():
    """GCSへの認証テスト"""
    auth = GoogleCloudAuth()
    
    # サービスアカウントファイルの存在確認
    if not auth.key_path or not os.path.exists(auth.key_path):
        pytest.skip(f"GCPサービスアカウントファイルが見つかりません: {auth.key_path}")
    
    # 認証を実行
    client = auth.authenticate_gcs()
    
    # 認証が成功したか確認
    assert client is not None, "認証に失敗しました"
    assert isinstance(client, storage.Client), "認証結果が正しいクライアントインスタンスではありません"
    
    print(f"GCS認証: OK")

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
    
    assert exists, f"データセット '{test_dataset}' が存在しません"
    print(f"データセット '{test_dataset}' の確認: OK")

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
    
    assert exists, f"テーブル '{test_dataset}.{test_table}' が存在しません"
    print(f"テーブル '{test_dataset}.{test_table}' の確認: OK")

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
    assert schema is not None, f"テーブル '{test_dataset}.{test_table}' のスキーマを取得できませんでした"
    assert len(schema) > 0, "スキーマにフィールドが含まれていません"
    
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
    
    assert exists, f"バケット '{test_bucket}' が存在しません"
    print(f"バケット '{test_bucket}' の確認: OK")

def test_upload_and_list_file():
    """ファイルのアップロードとリスト取得テスト"""
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
    
    # sample_files ディレクトリからサンプルファイルを探す
    sample_file_path = os.path.join(str(env.get_project_root()), "tests", "sample_files", "sample.txt")
    
    # サンプルファイルが存在しない場合は、その場でテスト用データを作成
    if not os.path.exists(sample_file_path):
        # サンプルファイル用ディレクトリがなければ作成
        sample_dir = os.path.dirname(sample_file_path)
        if not os.path.exists(sample_dir):
            os.makedirs(sample_dir)
            
        # テスト用の文字列データを作成してファイルに書き込む
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_content = f"これはテストファイルです。作成日時: {timestamp}"
        
        with open(sample_file_path, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        print(f"テスト用サンプルファイルを作成しました: {sample_file_path}")
    
    # タイムスタンプを含むGCS上のパスを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gcs_file_path = f"test/sample_file_{timestamp}.txt"
    
    # サンプルファイルをGCSにアップロード
    if os.path.exists(sample_file_path):
        uploaded_blob = auth.upload_file(sample_file_path, gcs_file_path, test_bucket)
        upload_source = f"ローカルファイル '{sample_file_path}'"
    else:
        # ファイルが見つからない場合は代替手段としてメモリ上のデータをアップロード
        test_content = f"これはメモリから生成されたテストファイルです。作成日時: {timestamp}"
        file_obj = io.BytesIO(test_content.encode('utf-8'))
        uploaded_blob = auth.upload_file(file_obj, gcs_file_path, test_bucket)
        upload_source = "メモリ上のデータ"
    
    # アップロードが成功したか確認
    assert uploaded_blob is not None, "ファイルのアップロードに失敗しました"
    
    # アップロードしたファイルがリストに含まれるか確認
    blobs = auth.list_blobs(test_bucket, prefix="test/")
    
    assert blobs is not None, "ファイル一覧の取得に失敗しました"
    
    # ファイル名の一覧を取得
    blob_names = [blob.name for blob in blobs]
    
    assert gcs_file_path in blob_names, f"アップロードしたファイル '{gcs_file_path}' がバケット内に見つかりません"
    
    # アップロード成功のログを出力
    print(f"\nGCSファイル操作 (バケット: {test_bucket}):")
    print(f" - {upload_source} から '{gcs_file_path}' へのアップロード: OK")
    print(f" - ファイル一覧取得: OK ({len(blobs)} ファイル)")
    
    # アップロードしたファイルリストを表示（最大5件）
    print("\nバケット内のファイル:")
    for i, blob in enumerate(blobs[:5]):
        print(f" - {i+1}. {blob.name} ({blob.size} バイト)")
    
    if len(blobs) > 5:
        print(f"... 他 {len(blobs) - 5} ファイル") 