#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
セレクタファイルの文字化けを修正するスクリプト
"""

import os
import sys
import csv
import json

# ファイルパス
INPUT_CSV = "data/page_analyze/updated/selectors_analysis.csv"
INPUT_JSON = "data/page_analyze/updated/selectors_analysis.json"
OUTPUT_CSV = "data/page_analyze/selectors_analysis_fixed.csv"
OUTPUT_JSON = "data/page_analyze/selectors_analysis_fixed.json"

# 日本語の説明マッピング
description_map = {
    "all_traffic_tab": "全トラフィックタブ（最高信頼度セレクタ）",
    "all_traffic_tab_xpath": "全トラフィックタブ（XPath）",
    "all_traffic_tab_text": "全トラフィックタブ（テキスト検索用）",
    "navbar": "ナビゲーションバー",
    "menu_nav": "メニューナビゲーション",
    "date_picker_trigger": "日付カレンダーを開くボタン",
    "date_input": "日付入力フィールド",
    "apply_button": "適用ボタン",
    "calendar_prev_month": "カレンダーの前月ボタン",
    "calendar_next_month": "カレンダーの次月ボタン",
    "download_csv_button": "CSVダウンロードボタン",
    "search_button": "検索ボタン",
    "refresh_button": "更新ボタン",
    "search_input": "検索入力フィールド",
    "checkbox_item": "チェックボックス",
    "radio_button": "ラジオボタン",
    "dropdown_select": "ドロップダウン選択",
    "data_table": "データテーブル",
    "table_header": "テーブルヘッダー",
    "table_body": "テーブル本体",
    "table_row": "テーブル行",
    "table_cell": "テーブルセル",
    "chart_container": "チャートコンテナ",
    "kpi_value": "KPI値",
    "report_title": "レポートタイトル"
}

def fix_csv_encoding():
    """CSVファイルの文字化けを修正"""
    try:
        # 修正されたセレクタを格納するリスト
        fixed_selectors = []
        
        # JSON形式のまま読み込む（既に正しくエンコードされている可能性）
        try:
            with open(INPUT_JSON, 'r', encoding='utf-8') as json_file:
                fixed_selectors = json.load(json_file)
                print(f"JSONファイルを読み込みました: {INPUT_JSON}")
        except Exception as json_e:
            print(f"JSONファイルの読み込みに失敗しました: {json_e}")
            
            # JSONファイルが読めなかった場合はCSVから読み込む
            with open(INPUT_CSV, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # 必要なフィールドが存在しなければスキップ
                    if not all(key in row for key in ['group', 'name', 'selector_type', 'selector_value']):
                        continue
                    
                    # 名前が説明マップにある場合は説明を修正
                    name = row.get('name', '')
                    description = description_map.get(name, row.get('description', ''))
                    
                    fixed_selector = {
                        'group': row.get('group', ''),
                        'name': name,
                        'selector_type': row.get('selector_type', ''),
                        'selector_value': row.get('selector_value', ''),
                        'description': description
                    }
                    
                    fixed_selectors.append(fixed_selector)
                
        # 修正したCSVを書き込み
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['group', 'name', 'selector_type', 'selector_value', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for selector in fixed_selectors:
                writer.writerow(selector)
        
        print(f"修正したCSVファイルを保存しました: {OUTPUT_CSV}")
        
        # JSONファイルとして保存
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as jsonfile:
            json.dump(fixed_selectors, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"修正したJSONファイルを保存しました: {OUTPUT_JSON}")
        
        return True
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    if fix_csv_encoding():
        print("文字化け修正が完了しました")
    else:
        print("文字化け修正に失敗しました")
        sys.exit(1) 