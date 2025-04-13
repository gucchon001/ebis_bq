#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汎用的なセレクタ情報作成スクリプト

このスクリプトは、EBiSの詳細分析ページと関連ページで使用される
汎用的なセレクタ情報を作成して、CSV/JSONファイルに出力します。
"""

import os
import sys
import argparse
import json
import csv
import shutil
from datetime import datetime
from typing import Dict, List, Any

# 設定
OUTPUT_DIR = "data/page_analyze"
BACKUP_DIR = os.path.join(OUTPUT_DIR, "backup")

# CSV/JSONファイル名
SELECTORS_CSV = "selectors_analysis.csv"
SELECTORS_JSON = "selectors_analysis.json"
REPORT_MD = "selectors_update_report.md"

def backup_existing_files(output_dir):
    """既存のセレクタファイルをバックアップ"""
    # バックアップディレクトリの作成
    backup_dir = os.path.join(output_dir, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # タイムスタンプを含む接尾辞を作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSVファイルのバックアップ
    csv_path = os.path.join(output_dir, SELECTORS_CSV)
    if os.path.exists(csv_path):
        backup_csv = os.path.join(backup_dir, f"{os.path.splitext(SELECTORS_CSV)[0]}_{timestamp}.csv")
        shutil.copy2(csv_path, backup_csv)
        print(f"CSVファイルをバックアップしました: {backup_csv}")
    
    # JSONファイルのバックアップ
    json_path = os.path.join(output_dir, SELECTORS_JSON)
    if os.path.exists(json_path):
        backup_json = os.path.join(backup_dir, f"{os.path.splitext(SELECTORS_JSON)[0]}_{timestamp}.json")
        shutil.copy2(json_path, backup_json)
        print(f"JSONファイルをバックアップしました: {backup_json}")
    
    return True

def create_page_selectors() -> List[Dict[str, Any]]:
    """
    ページで使用する汎用的なセレクタ情報を作成する
    
    Returns:
        List[Dict[str, Any]]: セレクタ情報のリスト
    """
    # セレクタ情報のリスト
    selectors = []
    
    # ナビゲーション関連のセレクタ
    navigation_selectors = [
        {
            "group": "detailed_analysis",
            "name": "all_traffic_tab",
            "text_value": "全トラフィック",
            "id": "navbar",
            "class": "nav-item nav-link",
            "css": "a[data-rb-event-key='all'] > div",
            "xpath": "//a[@data-rb-event-key='all']/div",
            "full_xpath": "//*[@id='navbar']/nav/a[2]/div",
            "element_type": "クリック可能",
            "category": "サイドバー",
            "data_rb_event_key": "all",
            "reliable_selectors": [
                {
                    "type": "css",
                    "value": "a[data-rb-event-key='all'] > div"
                },
                {
                    "type": "xpath",
                    "value": "//a[@data-rb-event-key='all']/div"
                }
            ]
        },
        {
            "group": "detailed_analysis",
            "name": "navbar",
            "text_value": "",
            "id": "navbar",
            "class": "",
            "css": "#navbar",
            "xpath": "//*[@id='navbar']",
            "full_xpath": "//*/html/body/div/div[2]/div/nav",
            "element_type": "コンテナ",
            "category": "ナビゲーション"
        },
        {
            "group": "detailed_analysis",
            "name": "menu_nav",
            "text_value": "",
            "id": "",
            "class": "nav",
            "css": "#navbar > nav",
            "xpath": "//nav",
            "full_xpath": "//*/html/body/div/div[2]/div/nav/nav",
            "element_type": "コンテナ",
            "category": "ナビゲーション"
        }
    ]
    
    # 日付範囲セレクタ
    date_range_selectors = [
        {
            "group": "detailed_analysis",
            "name": "date_picker_trigger",
            "text_value": "",
            "id": "",
            "class": "date-range-picker__input-container",
            "css": ".date-range-picker__input-container",
            "xpath": "//*[contains(@class, 'date-range-picker__input-container')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div",
            "element_type": "クリック可能",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "date_input",
            "text_value": "",
            "id": "",
            "class": "date-range-picker__input",
            "css": ".date-range-picker__input",
            "xpath": "//*[contains(@class, 'date-range-picker__input')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div/input",
            "element_type": "入力フィールド",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "apply_button",
            "text_value": "適用",
            "id": "",
            "class": "btn btn-primary",
            "css": ".date-range-picker__apply-button",
            "xpath": "/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]",
            "full_xpath": "/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]",
            "element_type": "クリック可能",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "calendar_prev_month",
            "text_value": "",
            "id": "",
            "class": "calendar-header__nav-button calendar-header__nav-button--prev",
            "css": ".calendar-header__nav-button--prev",
            "xpath": "//*[contains(@class, 'calendar-header__nav-button--prev')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div/div/button[1]",
            "element_type": "クリック可能",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "calendar_next_month",
            "text_value": "",
            "id": "",
            "class": "calendar-header__nav-button calendar-header__nav-button--next",
            "css": ".calendar-header__nav-button--next",
            "xpath": "//*[contains(@class, 'calendar-header__nav-button--next')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div/div/button[2]",
            "element_type": "クリック可能",
            "category": "フィルター"
        }
    ]
    
    # ボタンとアクション関連のセレクタ
    button_selectors = [
        {
            "group": "detailed_analysis",
            "name": "download_csv_button",
            "text_value": "CSV",
            "id": "",
            "class": "btn btn-outline-secondary btn-sm",
            "css": "#common-bar .btn-outline-secondary",
            "xpath": "//*[@id='common-bar']/div[2]/nav/div[2]/div[4]/div[2]/a",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[4]/div[2]/a",
            "element_type": "クリック可能",
            "category": "ボタン"
        },
        {
            "group": "detailed_analysis",
            "name": "search_button",
            "text_value": "検索",
            "id": "",
            "class": "btn btn-primary",
            "css": "button.btn-primary",
            "xpath": "//button[contains(@class, 'btn-primary')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[3]/div/button",
            "element_type": "クリック可能",
            "category": "ボタン"
        },
        {
            "group": "detailed_analysis",
            "name": "refresh_button",
            "text_value": "更新",
            "id": "",
            "class": "btn btn-refresh btn-sm",
            "css": "button.btn-refresh",
            "xpath": "//button[contains(@class, 'btn-refresh')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[5]/button",
            "element_type": "クリック可能",
            "category": "ボタン"
        }
    ]
    
    # 入力要素のセレクタ
    input_selectors = [
        {
            "group": "detailed_analysis",
            "name": "search_input",
            "text_value": "",
            "id": "",
            "class": "form-control",
            "css": "input[type='text'][placeholder*='検索']",
            "xpath": "//input[@type='text' and contains(@placeholder, '検索')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[3]/div/div/input",
            "element_type": "入力フィールド",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "checkbox_item",
            "text_value": "",
            "id": "",
            "class": "form-check-input",
            "css": "input[type='checkbox']",
            "xpath": "//input[@type='checkbox']",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[2]/div/div/div/input",
            "element_type": "入力フィールド",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "radio_button",
            "text_value": "",
            "id": "",
            "class": "form-check-input",
            "css": "input[type='radio']",
            "xpath": "//input[@type='radio']",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[2]/div/div/div/div/input",
            "element_type": "入力フィールド",
            "category": "フィルター"
        },
        {
            "group": "detailed_analysis",
            "name": "dropdown_select",
            "text_value": "",
            "id": "",
            "class": "form-control",
            "css": "select.form-control",
            "xpath": "//select[contains(@class, 'form-control')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[2]/div/div/select",
            "element_type": "入力フィールド",
            "category": "フィルター"
        }
    ]
    
    # テーブル関連のセレクタ
    table_selectors = [
        {
            "group": "detailed_analysis",
            "name": "data_table",
            "text_value": "",
            "id": "",
            "class": "table",
            "css": "table.table",
            "xpath": "//table[contains(@class, 'table')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[3]/div/table",
            "element_type": "テーブル",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "table_header",
            "text_value": "",
            "id": "",
            "class": "",
            "css": "table.table > thead",
            "xpath": "//table[contains(@class, 'table')]/thead",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[3]/div/table/thead",
            "element_type": "テーブル",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "table_body",
            "text_value": "",
            "id": "",
            "class": "",
            "css": "table.table > tbody",
            "xpath": "//table[contains(@class, 'table')]/tbody",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[3]/div/table/tbody",
            "element_type": "テーブル",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "table_row",
            "text_value": "",
            "id": "",
            "class": "",
            "css": "table.table > tbody > tr",
            "xpath": "//table[contains(@class, 'table')]/tbody/tr",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[3]/div/table/tbody/tr",
            "element_type": "テーブル",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "table_cell",
            "text_value": "",
            "id": "",
            "class": "",
            "css": "table.table > tbody > tr > td",
            "xpath": "//table[contains(@class, 'table')]/tbody/tr/td",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[3]/div/table/tbody/tr/td",
            "element_type": "テーブル",
            "category": "データ表示"
        }
    ]
    
    # レポート関連のセレクタ
    report_selectors = [
        {
            "group": "detailed_analysis",
            "name": "chart_container",
            "text_value": "",
            "id": "",
            "class": "chart-container",
            "css": ".chart-container",
            "xpath": "//*[contains(@class, 'chart-container')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div[2]/div/div",
            "element_type": "グラフ",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "kpi_value",
            "text_value": "",
            "id": "",
            "class": "kpi-value",
            "css": ".kpi-value",
            "xpath": "//*[contains(@class, 'kpi-value')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div/div/div[2]/div",
            "element_type": "テキスト",
            "category": "データ表示"
        },
        {
            "group": "detailed_analysis",
            "name": "report_title",
            "text_value": "",
            "id": "",
            "class": "report-title",
            "css": ".report-title",
            "xpath": "//*[contains(@class, 'report-title')]",
            "full_xpath": "//*/html/body/div[1]/div[2]/div[2]/div[2]/div/div/div/div/h2",
            "element_type": "テキスト",
            "category": "データ表示"
        }
    ]
    
    # セレクタを統合
    selectors.extend(navigation_selectors)
    selectors.extend(date_range_selectors)
    selectors.extend(button_selectors)
    selectors.extend(input_selectors)
    selectors.extend(table_selectors)
    selectors.extend(report_selectors)
    
    return selectors

def save_selectors_to_csv(selectors, output_path):
    """
    セレクタ情報をCSVファイルに保存
    
    Args:
        selectors (List[Dict]): セレクタ情報のリスト
        output_path (str): 保存先ファイルパス
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        # selectors_analysis.jsonと同じフィールド構造を使用
        fieldnames = ['group', 'name', 'text_value', 'id', 'class', 'css', 'xpath', 'full_xpath', 'element_type', 'category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for selector in selectors:
            # 必要なフィールドだけを抽出
            row = {field: selector.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"CSVファイルを保存しました: {output_path}")

def save_selectors_to_json(selectors, output_path):
    """
    セレクタ情報をJSONファイルに保存
    
    Args:
        selectors (List[Dict]): セレクタ情報のリスト
        output_path (str): 保存先ファイルパス
    """
    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(selectors, jsonfile, ensure_ascii=False, indent=2)
    
    print(f"JSONファイルを保存しました: {output_path}")

def create_update_report(output_dir, selectors):
    """
    更新レポートを作成
    
    Args:
        output_dir (str): 出力ディレクトリ
        selectors (List[Dict]): セレクタ情報のリスト
    """
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    # カテゴリ別にセレクタを分類
    categorized_selectors = {}
    for selector in selectors:
        group = selector.get("group", "other")
        if group not in categorized_selectors:
            categorized_selectors[group] = []
        categorized_selectors[group].append(selector)
    
    # レポートの内容を作成
    report_content = f"""# セレクタ更新レポート

## 更新内容
EBiSの詳細分析ページで利用できる汎用的なセレクタ情報を更新しました。
すべてのクリック可能要素と入力要素に対応するセレクタが含まれています。

## 更新したファイル
- `{SELECTORS_CSV}`
- `{SELECTORS_JSON}`

## 主なセレクタ情報

"""
    
    # グループ別にセレクタ情報を追加
    for group, group_selectors in categorized_selectors.items():
        report_content += f"### {group}グループのセレクタ\n\n```\n"
        for selector in group_selectors:
            report_content += f"{selector['group']},{selector['name']},{selector['element_type']},{selector['css']},{selector.get('category', '')}\n"
        report_content += "```\n\n"
    
    report_content += f"""## 更新日時
{now}
"""
    
    # レポートファイルを書き込み
    report_path = os.path.join(output_dir, REPORT_MD)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"更新レポートを作成しました: {report_path}")

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="汎用的なセレクタ情報作成スクリプト")
    parser.add_argument("--output-dir", help="出力ディレクトリを指定", default=OUTPUT_DIR)
    args = parser.parse_args()
    
    output_dir = args.output_dir
    
    print("===================================================")
    print("汎用的なセレクタ情報の作成を開始します")
    print("===================================================")
    print(f"出力ディレクトリ: {output_dir}")
    
    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)
    
    # 既存ファイルのバックアップ
    backup_existing_files(output_dir)
    
    # 汎用的なセレクタ情報を作成
    selectors = create_page_selectors()
    
    # CSVファイルとJSONファイルに保存
    csv_path = os.path.join(output_dir, SELECTORS_CSV)
    json_path = os.path.join(output_dir, SELECTORS_JSON)
    
    save_selectors_to_csv(selectors, csv_path)
    save_selectors_to_json(selectors, json_path)
    
    # 更新レポートを作成
    create_update_report(output_dir, selectors)
    
    print("\n===================================================")
    print("セレクタ情報の作成が完了しました")
    print("===================================================")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 