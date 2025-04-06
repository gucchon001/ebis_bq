#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Spreadsheetへの認証機能

環境変数から認証情報を取得し、Google Spreadsheetに認証するための最小限の機能を提供します。
"""

import os
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from src.utils.logging_config import get_logger
from src.utils.environment import env

logger = get_logger(__name__)

class SpreadsheetAuth:
    """
    Google Spreadsheetへの認証を処理する最小限のクラス
    """
    
    def __init__(self):
        """
        SpreadsheetAuthの初期化
        環境変数から設定を自動読み込み
        """
        # 環境変数を読み込む
        try:
            env.load_env()
        except Exception as e:
            logger.warning(f"環境変数の読み込みに失敗しました: {e}")
        
        # サービスアカウントファイルのパスを環境変数から取得
        self.service_account_path = env.get_env_var('SERVICE_ACCOUNT_FILE', 'config/spreadsheet.json')
        
        # プロジェクトルートからの相対パスを解決
        if not os.path.isabs(self.service_account_path):
            self.service_account_path = os.path.join(
                str(env.get_project_root()), 
                self.service_account_path
            )
        
        logger.info(f"サービスアカウントファイル: {self.service_account_path}")
        
        # 認証用クライアント
        self.client = None
    
    def authenticate(self) -> Optional[gspread.Client]:
        """
        Google APIに認証する
        
        Returns:
            Optional[gspread.Client]: 認証済みのgspreadクライアント、失敗時はNone
        """
        if not os.path.exists(self.service_account_path):
            logger.error(f"サービスアカウントファイルが見つかりません: {self.service_account_path}")
            return None
        
        try:
            # 認証スコープ
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # サービスアカウントから認証情報を取得
            credentials = Credentials.from_service_account_file(
                self.service_account_path, 
                scopes=scopes
            )
            
            # gspreadクライアントの認証
            self.client = gspread.authorize(credentials)
            logger.info("Google Spreadsheet APIへの認証に成功しました")
            return self.client
            
        except Exception as e:
            logger.error(f"Google APIへの認証に失敗しました: {str(e)}")
            return None
    
    def get_spreadsheet(self, spreadsheet_id: str) -> Optional[gspread.Spreadsheet]:
        """
        指定されたIDのスプレッドシートを取得する
        
        Args:
            spreadsheet_id (str): スプレッドシートID
            
        Returns:
            Optional[gspread.Spreadsheet]: スプレッドシート、失敗時はNone
        """
        if self.client is None:
            self.client = self.authenticate()
            if self.client is None:
                return None
        
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            logger.info(f"スプレッドシートを開きました: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            logger.error(f"スプレッドシートを開けませんでした: {str(e)}")
            return None
    
    @staticmethod
    def get_instance() -> 'SpreadsheetAuth':
        """
        SpreadsheetAuthのシングルトンインスタンスを取得
        
        Returns:
            SpreadsheetAuth: SpreadsheetAuthのインスタンス
        """
        return SpreadsheetAuth()