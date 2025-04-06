#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQuery/GCSクライアント (最小限バージョン)

Google BigQueryとGoogle Cloud Storageとの連携に必要な最小限の機能を提供します。
- GCS認証
- BigQuery認証
- テーブルスキーマ確認
- GCSファイル操作
"""

import os
from pathlib import Path
from typing import Optional, List, BinaryIO, Union

from google.cloud import bigquery
from google.cloud import storage
from google.oauth2 import service_account
from google.cloud.exceptions import NotFound

from src.utils.logging_config import get_logger
from src.utils.environment import env

logger = get_logger(__name__)

class GoogleCloudAuth:
    """Google BigQueryとGCSへの認証を行うユーティリティクラス"""

    def __init__(self, key_path: Optional[str] = None):
        """
        GoogleCloudAuthの初期化
        
        Args:
            key_path (Optional[str]): サービスアカウントのJSONファイルパス。
                                     指定しない場合は環境変数から読み込み
        """
        # 環境変数を読み込む
        try:
            env.load_env()
        except Exception as e:
            logger.warning(f"環境変数の読み込みに失敗しました: {e}")
        
        # 設定を環境変数から取得
        self.project_id = env.get_env_var("PROJECT_ID")
        self.dataset_id = env.get_env_var("BIGQUERY_DATASET")
        self.bucket_name = env.get_env_var("GCS_BUCKET_NAME")
        
        # キーファイルのパス取得
        if key_path is None:
            key_path = env.get_env_var("GOOGLE_APPLICATION_CREDENTIALS")
        
        # 相対パスを絶対パスに解決
        if key_path and not os.path.isabs(key_path):
            key_path = os.path.join(str(env.get_project_root()), key_path)
        
        self.key_path = key_path
        self.credentials = None
        self.bigquery_client = None
        self.storage_client = None
        
        logger.info(f"GoogleCloudAuthを初期化しました: プロジェクトID={self.project_id}")
    
    def get_credentials(self) -> Optional[service_account.Credentials]:
        """
        Google Cloud認証情報を取得
        
        Returns:
            Optional[service_account.Credentials]: 認証情報、失敗時はNone
        """
        if self.credentials:
            return self.credentials
            
        if not self.key_path or not os.path.exists(self.key_path):
            logger.error(f"認証キーファイルが見つかりません: {self.key_path}")
            return None
        
        try:
            # 認証情報を作成
            self.credentials = service_account.Credentials.from_service_account_file(
                self.key_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            return self.credentials
        except Exception as e:
            logger.error(f"認証情報取得中にエラーが発生しました: {str(e)}")
            return None
    
    def authenticate_bigquery(self) -> Optional[bigquery.Client]:
        """
        BigQuery認証を行い、クライアントを取得
        
        Returns:
            Optional[bigquery.Client]: 認証済みのBigQueryクライアント、失敗時はNone
        """
        if self.bigquery_client:
            return self.bigquery_client
            
        credentials = self.get_credentials()
        if not credentials:
            return None
        
        try:
            # BigQueryクライアントを初期化
            self.bigquery_client = bigquery.Client(
                credentials=credentials,
                project=self.project_id
            )
            
            logger.info("BigQuery認証が完了しました")
            return self.bigquery_client
            
        except Exception as e:
            logger.error(f"BigQuery認証処理中にエラーが発生しました: {str(e)}")
            return None
    
    def authenticate_gcs(self) -> Optional[storage.Client]:
        """
        Google Cloud Storage認証を行い、クライアントを取得
        
        Returns:
            Optional[storage.Client]: 認証済みのGCSクライアント、失敗時はNone
        """
        if self.storage_client:
            return self.storage_client
            
        credentials = self.get_credentials()
        if not credentials:
            return None
        
        try:
            # GCSクライアントを初期化
            self.storage_client = storage.Client(
                credentials=credentials,
                project=self.project_id
            )
            
            logger.info("Google Cloud Storage認証が完了しました")
            return self.storage_client
            
        except Exception as e:
            logger.error(f"GCS認証処理中にエラーが発生しました: {str(e)}")
            return None
    
    def dataset_exists(self, dataset_id: Optional[str] = None) -> bool:
        """
        指定されたデータセットが存在するか確認
        
        Args:
            dataset_id (Optional[str]): 確認するデータセットID
            
        Returns:
            bool: データセットが存在する場合はTrue
        """
        client = self.authenticate_bigquery()
        if not client:
            return False
        
        dataset_id = dataset_id or self.dataset_id
        if not dataset_id:
            logger.error("データセットIDが指定されていません")
            return False
        
        try:
            # 推奨される方法でデータセットの存在を確認
            dataset_ref = f"{self.project_id}.{dataset_id}"
            client.get_dataset(dataset_ref)  # API呼び出しでデータセットを取得
            logger.info(f"データセット '{dataset_id}' は存在します")
            return True
        except NotFound:
            logger.info(f"データセット '{dataset_id}' は存在しません")
            return False
        except Exception as e:
            logger.error(f"データセット確認中にエラーが発生しました: {str(e)}")
            return False
    
    def table_exists(self, table_id: str, dataset_id: Optional[str] = None) -> bool:
        """
        指定されたテーブルが存在するか確認
        
        Args:
            table_id (str): 確認するテーブルID
            dataset_id (Optional[str]): データセットID
            
        Returns:
            bool: テーブルが存在する場合はTrue
        """
        client = self.authenticate_bigquery()
        if not client:
            return False
        
        dataset_id = dataset_id or self.dataset_id
        if not dataset_id:
            logger.error("データセットIDが指定されていません")
            return False
        
        try:
            # 推奨される方法でテーブルの存在を確認
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            client.get_table(table_ref)  # API呼び出しでテーブルを取得
            logger.info(f"テーブル '{dataset_id}.{table_id}' は存在します")
            return True
        except NotFound:
            logger.info(f"テーブル '{dataset_id}.{table_id}' は存在しません")
            return False
        except Exception as e:
            logger.error(f"テーブル確認中にエラーが発生しました: {str(e)}")
            return False
    
    def get_table_schema(self, table_id: str, dataset_id: Optional[str] = None) -> Optional[List[bigquery.SchemaField]]:
        """
        テーブルのスキーマを取得
        
        Args:
            table_id (str): テーブルID
            dataset_id (Optional[str]): データセットID
            
        Returns:
            Optional[List[bigquery.SchemaField]]: スキーマ情報、失敗時はNone
        """
        client = self.authenticate_bigquery()
        if not client:
            return None
        
        dataset_id = dataset_id or self.dataset_id
        if not dataset_id:
            logger.error("データセットIDが指定されていません")
            return None
        
        try:
            # 推奨される方法でテーブルの参照を取得
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            table = client.get_table(table_ref)  # API呼び出しでテーブルを取得
            
            logger.info(f"テーブル '{dataset_id}.{table_id}' のスキーマを取得しました")
            
            # スキーマ情報をログに出力
            for field in table.schema:
                logger.debug(f"フィールド: {field.name}, 型: {field.field_type}, モード: {field.mode}")
            
            return table.schema
        except NotFound:
            logger.warning(f"テーブル '{dataset_id}.{table_id}' が見つかりません")
            return None
        except Exception as e:
            logger.error(f"スキーマ取得中にエラーが発生しました: {str(e)}")
            return None
    
    def bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        指定されたバケットが存在するか確認
        
        Args:
            bucket_name (Optional[str]): 確認するバケット名
            
        Returns:
            bool: バケットが存在する場合はTrue
        """
        client = self.authenticate_gcs()
        if not client:
            return False
        
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            logger.error("バケット名が指定されていません")
            return False
        
        try:
            bucket = client.get_bucket(bucket_name)
            logger.info(f"バケット '{bucket_name}' は存在します")
            return True
        except NotFound:
            logger.info(f"バケット '{bucket_name}' は存在しません")
            return False
        except Exception as e:
            logger.error(f"バケット確認中にエラーが発生しました: {str(e)}")
            return False
    
    def list_blobs(self, bucket_name: Optional[str] = None, prefix: str = "") -> Optional[List[storage.Blob]]:
        """
        バケット内のファイル一覧を取得
        
        Args:
            bucket_name (Optional[str]): バケット名
            prefix (str): フィルタリング用のプレフィックス
            
        Returns:
            Optional[List[storage.Blob]]: ファイル一覧、失敗時はNone
        """
        client = self.authenticate_gcs()
        if not client:
            return None
        
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            logger.error("バケット名が指定されていません")
            return None
        
        try:
            bucket = client.get_bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))
            
            logger.info(f"バケット '{bucket_name}' 内のファイル数: {len(blobs)}")
            return blobs
        except Exception as e:
            logger.error(f"ファイル一覧取得中にエラーが発生しました: {str(e)}")
            return None
    
    def upload_file(self, 
                   source_file: Union[str, BinaryIO], 
                   destination_blob_name: str, 
                   bucket_name: Optional[str] = None) -> Optional[storage.Blob]:
        """
        ファイルをGCSにアップロード
        
        Args:
            source_file (Union[str, BinaryIO]): アップロードするファイルのパスまたはファイルオブジェクト
            destination_blob_name (str): 保存先のGCS上のパス
            bucket_name (Optional[str]): バケット名
            
        Returns:
            Optional[storage.Blob]: アップロードされたBlob、失敗時はNone
        """
        client = self.authenticate_gcs()
        if not client:
            return None
        
        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            logger.error("バケット名が指定されていません")
            return None
        
        try:
            bucket = client.get_bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            # ファイルパスまたはファイルオブジェクトに基づいてアップロード
            if isinstance(source_file, str):
                blob.upload_from_filename(source_file)
                logger.info(f"ファイル '{source_file}' を '{bucket_name}/{destination_blob_name}' にアップロードしました")
            else:
                blob.upload_from_file(source_file)
                logger.info(f"ファイルオブジェクトを '{bucket_name}/{destination_blob_name}' にアップロードしました")
            
            return blob
        except Exception as e:
            logger.error(f"ファイルアップロード中にエラーが発生しました: {str(e)}")
            return None
    
    @staticmethod
    def get_instance() -> 'GoogleCloudAuth':
        """
        GoogleCloudAuthのインスタンスを取得
        
        Returns:
            GoogleCloudAuth: GoogleCloudAuthのインスタンス
        """
        return GoogleCloudAuth()


# 後方互換性のために別名を提供
BigQueryAuth = GoogleCloudAuth 