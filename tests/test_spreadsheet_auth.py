#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Spreadsheet認証のテスト

サービスアカウントファイルの存在と実際の認証をテストします。
指定されたテスト用スプレッドシートにアクセスしてデータの読み取りも確認します。
"""

import os
import pytest
import gspread

from src.utils.spreadsheet import SpreadsheetAuth
from src.utils.environment import env

def test_service_account_file_exists(environment):
    """サービスアカウントファイルが存在するかテスト"""
    # SpreadsheetAuthをインスタンス化
    auth = SpreadsheetAuth()
    
    # サービスアカウントファイルのパスを取得
    service_account_path = auth.service_account_path
    
    # ファイルの存在確認
    file_exists = os.path.exists(service_account_path)
    
    if not file_exists:
        pytest.skip(f"サービスアカウントファイルが見つかりません: {service_account_path}")
    
    assert file_exists, f"サービスアカウントファイルが存在しません: {service_account_path}"
    print(f"サービスアカウントファイルの確認: OK - {service_account_path}")

def test_spreadsheet_auth():
    """実際のGoogle APIへの認証テスト"""
    # SpreadsheetAuthをインスタンス化
    auth = SpreadsheetAuth()
    
    # サービスアカウントファイルの存在確認
    if not os.path.exists(auth.service_account_path):
        pytest.skip(f"サービスアカウントファイルが見つかりません: {auth.service_account_path}")
    
    # 認証を実行
    client = auth.authenticate()
    
    # 認証が成功したか確認
    assert client is not None, "認証に失敗しました"
    assert isinstance(client, gspread.Client), "認証結果が正しいクライアントインスタンスではありません"
    
    print(f"Google APIへの認証: OK")

def test_spreadsheet_access():
    """スプレッドシートへのアクセステスト"""
    # スプレッドシートIDを環境設定から取得
    spreadsheet_id = env.get_config_value('SPREADSHEET', 'SSID', '').strip('"\'')
    
    # 設定値が空または無効な場合はスキップ
    if not spreadsheet_id or spreadsheet_id == '':
        pytest.skip("スプレッドシートIDが設定されていません。settings.iniの[SPREADSHEET]セクションを確認してください。")
    
    # SpreadsheetAuthをインスタンス化して認証
    auth = SpreadsheetAuth()
    
    # サービスアカウントファイルの存在確認
    if not os.path.exists(auth.service_account_path):
        pytest.skip(f"サービスアカウントファイルが見つかりません: {auth.service_account_path}")
    
    # スプレッドシートを取得
    spreadsheet = auth.get_spreadsheet(spreadsheet_id)
    
    # スプレッドシートが取得できたか確認
    assert spreadsheet is not None, "スプレッドシートの取得に失敗しました"
    
    # スプレッドシートのタイトルを表示
    print(f"接続したスプレッドシート: {spreadsheet.title}")
    
    # ワークシート一覧を取得して表示
    worksheets = spreadsheet.worksheets()
    assert len(worksheets) > 0, "スプレッドシートにワークシートがありません"
    
    print(f"ワークシート一覧:")
    for sheet in worksheets:
        print(f" - {sheet.title} (ID: {sheet.id})")

def test_spreadsheet_data_read():
    """スプレッドシートからデータを読み取るテスト"""
    # スプレッドシートIDを環境設定から取得
    spreadsheet_id = env.get_config_value('SPREADSHEET', 'SSID', '').strip('"\'')
    
    # シート名を環境設定から取得
    sheet_name = env.get_config_value('SPREADSHEET', 'TEST_SHEET', '')
    
    # 設定値が空または無効な場合はスキップ
    if not spreadsheet_id or spreadsheet_id == '':
        pytest.skip("スプレッドシートIDが設定されていません。settings.iniの[SPREADSHEET]セクションを確認してください。")
    
    if not sheet_name or sheet_name == '':
        pytest.skip("テストシート名が設定されていません。settings.iniの[SPREADSHEET]セクションを確認してください。")
    
    # SpreadsheetAuthをインスタンス化して認証
    auth = SpreadsheetAuth()
    
    # サービスアカウントファイルの存在確認
    if not os.path.exists(auth.service_account_path):
        pytest.skip(f"サービスアカウントファイルが見つかりません: {auth.service_account_path}")
    
    # スプレッドシートを取得
    spreadsheet = auth.get_spreadsheet(spreadsheet_id)
    if spreadsheet is None:
        pytest.skip("スプレッドシートに接続できませんでした")
    
    try:
        # テスト用シートを開く
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # すべての値を取得
        all_values = worksheet.get_all_values()
        
        # データが存在するか確認
        assert len(all_values) > 0, "スプレッドシートにデータがありません"
        assert len(all_values[0]) > 0, "スプレッドシートの行にデータがありません"
        
        # ヘッダー行の確認
        header_row = all_values[0]
        print(f"ヘッダー行: {header_row}")
        
        # データ行の確認（最初の数行だけ表示）
        print(f"データ行のサンプル（最大5行）:")
        for i, row in enumerate(all_values[1:6]):  # 最大5行表示
            print(f"  行 {i+1}: {row}")
        
        print(f"スプレッドシートからのデータ読み取り: OK（{len(all_values)-1}行のデータ）")
        
    except gspread.exceptions.WorksheetNotFound:
        pytest.skip(f"ワークシート '{sheet_name}' が見つかりません")
    except Exception as e:
        pytest.fail(f"テスト中にエラーが発生しました: {str(e)}") 