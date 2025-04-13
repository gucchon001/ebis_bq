#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EBiSページ解析ツール

ページ上の様々な要素を識別し、クリック可能な要素や入力フィールドを検出して、
高精度のセレクタを生成するために使用されます。
全ての操作可能要素を汎用的に検出し、それぞれのセレクタをCSVやJSONで出力できます。

主な機能:
- クリック可能要素と入力フォームの自動検出
- 要素の分類とカテゴリ分け
- ID、CSS、XPathなど複数形式のセレクタ生成
- JavaScriptを活用した高精度な要素検出
- 結果のCSV/JSON形式での出力

最適化済み:
- 重複コードの削減と共通処理の関数化
- エラーハンドリングの統一
- 冗長なコード部分の簡素化
- パフォーマンスとメモリ使用量の改善
"""

import os
import sys
import time
import json
import csv
import logging
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import pandas as pd
from tabulate import tabulate
import collections
import re

# プロジェクト固有のインポート
from src.utils.logging_config import get_logger
from src.utils.environment import env
# 正しいモジュールパスに修正
from src.modules.selenium.browser import Browser
from src.modules.selenium.page_analyzer import PageAnalyzer
from src.modules.ebis.login_page import login

# ロガーの初期化
logger = get_logger(__name__)

# 出力ディレクトリのデフォルト値
OUTPUT_DIR = os.path.join("data", "page_analyze")

class ElementInfo:
    """
    ページ上の要素情報を保持するクラス
    """
    def __init__(self, element=None, tag=None, text=None, attrs=None, category=None):
        self.element = element
        self.tag = tag or (element.tag_name if element else "")
        self.text = text or (element.text if element else "")
        self.attrs = attrs or {}
        self.category = category or "その他"  # カテゴリー情報を追加
        
    def __str__(self):
        return f"{self.tag}: {self.text[:30]}{'...' if len(self.text) > 30 else ''}"
        
    def as_dict(self):
        """辞書形式で返す"""
        return {
            "タグ": self.tag,
            "テキスト": self.text[:50] + ('...' if len(self.text) > 50 else ''),
            "表示状態": self.attrs.get("is_displayed", False),
            "有効状態": self.attrs.get("is_enabled", False),
            "ID": self.attrs.get("id", ""),
            "クラス": self.attrs.get("class", ""),
            "カテゴリー": self.category
        }

    @property
    def is_displayed(self):
        return self.attrs.get("is_displayed", False)
        
    @property
    def is_enabled(self):
        return self.attrs.get("is_enabled", False)

    def get_selectors(self):
        """要素のセレクタ情報を取得"""
        selectors = {}
        reliable_selectors = []
        
        # ID属性があればIDセレクタを追加
        element_id = self.attrs.get("id", "")
        if element_id and element_id.strip():
            selectors["id"] = element_id
            selectors["css"] = f"#{element_id}"
            reliable_selectors.append({
                "type": "css", 
                "value": f"#{element_id}"
            })
            
        # CSSセレクタの生成
        # 1. クラス属性に基づく簡易CSSセレクタを保持
        element_class = self.attrs.get("class", "")
        if element_class and element_class.strip():
            selectors["class"] = element_class
            # クラス名に基づく簡易CSSセレクタ (後方互換性のため残す)
            selectors["css_simple"] = f".{element_class.replace(' ', '.')}"
        else:
            selectors["class"] = ""
            # タグ名がある場合は基本的なCSSセレクタを生成
            if self.tag:
                selectors["css_simple"] = self.tag
            else:
                selectors["css_simple"] = "div"  # デフォルト
        
        # 2. 詳細なCSSセレクタを設定
        css_path = self.attrs.get("css_path", "")
        if css_path:
            # css_pathがあれば階層構造を含む詳細なCSSセレクタとして使用
            selectors["css"] = css_path
        elif not element_id:
            # IDがない場合は他の方法でCSSセレクタを生成
            
            # データ属性を使用したセレクタ
            data_attr_selector = None
            for attr, value in self.attrs.items():
                if attr.startswith("data-") and value and value.strip():
                    value = value.replace("'", "\\'")  # シングルクォートをエスケープ
                    data_attr_selector = f"{self.tag}[{attr}='{value}']"
                    break
            
            if data_attr_selector:
                selectors["css"] = data_attr_selector
            elif element_class and self.tag:
                # クラスと要素名を組み合わせたセレクタ
                classes = element_class.split()
                # 重要なクラスを優先
                important_classes = [c for c in classes if re.search(r'^(nav|menu|btn|button|tab|header|footer|main|content|row|col)', c) or 
                                   c in ['active', 'selected', 'primary', 'secondary', 'container']]
                
                if important_classes:
                    # 重要なクラスを最大2つ使用
                    selectors["css"] = f"{self.tag}.{'.'.join(important_classes[:2])}"
                elif classes:
                    # 重要でないクラスは1つだけ使用
                    selectors["css"] = f"{self.tag}.{classes[0]}"
                else:
                    selectors["css"] = selectors.get("css_simple", self.tag or "div")
            else:
                # フォールバックとしてシンプルなセレクタを使用
                selectors["css"] = selectors.get("css_simple", self.tag or "div")
        
        # 3. XPathセレクタの生成
        xpath = self.attrs.get("xpath", "")
        if xpath:
            selectors["xpath"] = xpath
        else:
            # 基本的なXPathセレクタを生成
            if self.tag:
                selectors["xpath"] = f"//{self.tag}"
                # IDがある場合はIDを使用
                if element_id:
                    selectors["xpath"] = f"//{self.tag}[@id='{element_id}']"
                # クラスがある場合はクラスを使用
                elif element_class:
                    clean_class = element_class.replace("'", "\\'")  # シングルクォートをエスケープ
                    selectors["xpath"] = f"//{self.tag}[@class='{clean_class}']"
            else:
                selectors["xpath"] = "//div"  # デフォルト
        
        # 4. 完全なXPathセレクタを追加（要素の完全なパス）
        full_xpath = self.attrs.get("full_xpath", "")
        if full_xpath:
            selectors["full_xpath"] = full_xpath
        else:
            # xpathがある場合はそれをfull_xpathとしても使用（互換性のため）
            selectors["full_xpath"] = selectors.get("xpath", "//div")
        
        # 信頼性の高いセレクタのリストを生成
        if not reliable_selectors:
            # IDセレクタがない場合のセレクタ優先順位
            
            # 詳細なCSSセレクタを追加
            if css_path or "css" in selectors and selectors["css"] != self.tag:
                reliable_selectors.append({
                    "type": "css", 
                    "value": selectors["css"]
                })
            elif "css_simple" in selectors and selectors["css_simple"] and selectors["css_simple"] != self.tag:
                reliable_selectors.append({
                    "type": "css",
                    "value": selectors["css_simple"]
                })
            
            # テキストベースのXPathセレクタを追加
            if self.text and self.text.strip() and self.tag:
                safe_text = self.text.replace("'", "\\'")
                text_xpath = f"//{self.tag}[text()='{safe_text}']"
                reliable_selectors.append({
                    "type": "xpath", 
                    "value": text_xpath
                })
            
            # 通常のXPathセレクタを追加
            if "xpath" in selectors and selectors["xpath"] and selectors["xpath"] != f"//{self.tag or 'div'}":
                if not any(s["value"] == selectors["xpath"] for s in reliable_selectors):
                    reliable_selectors.append({
                        "type": "xpath",
                        "value": selectors["xpath"]
                    })
            
            # full_xpathがあり、xpathと異なる場合は追加
            if "full_xpath" in selectors and selectors["full_xpath"] != selectors.get("xpath", "") and selectors["full_xpath"] != f"//{self.tag or 'div'}":
                if not any(s["value"] == selectors["full_xpath"] for s in reliable_selectors):
                    reliable_selectors.append({
                        "type": "xpath",
                        "value": selectors["full_xpath"]
                    })
            
            # どのセレクタも作成できなかった場合は、フォールバックセレクタを追加
            if not reliable_selectors and self.tag:
                reliable_selectors.append({
                    "type": "css",
                    "value": self.tag
                })
            
            # 最後の手段として、divのセレクタを追加
            if not reliable_selectors:
                reliable_selectors.append({
                    "type": "css",
                    "value": "div"
                })
        
        # 最終的なセレクタ情報を設定
        selectors["reliable_selectors"] = reliable_selectors
        return selectors


class PageAnalyzerTool:
    """
    ページ解析ツールクラス
    
    ページ上の要素を分析し、クリック可能な要素とセレクタ情報を抽出します
    """
    
    def __init__(self, headless=False, output_dir=None):
        """
        初期化
        
        Args:
            headless (bool): ヘッドレスモードで実行するかどうか
            output_dir (str): 出力ディレクトリ
        """
        # ロガー設定
        self.logger = get_logger(__name__)
        
        # ヘッドレスモード設定
        self.headless = headless
        
        # 出力ディレクトリの設定（指定がなければデフォルト値を使用）
        self.output_dir = output_dir or OUTPUT_DIR
        
        # 出力ディレクトリの存在確認と作成
        os.makedirs(self.output_dir, exist_ok=True)
        
        # ブラウザインスタンス
        self.browser = None
        
        # PageAnalyzerインスタンス
        self.page_analyzer = None
        
        # 収集した要素の保存用
        self.elements = {
            "clickable": [],  # クリック可能な要素
            "input": []       # 入力フィールド
        }
        
        # クリック可能な要素と入力要素のリスト
        self.clickable_elements = []
        self.input_elements = []
        
        # ページの構造情報
        self.page_structure = {
            "sidebar": None,
            "top_bar": None,
            "content": None,
            "navigation": None
        }
        
        # 特殊アイテムのXPathマッピング（汎用実装では空の辞書）
        self.special_item_xpath_map = {}
        
        # カテゴリー別の要素リスト
        self.categorized_elements = {
            "トップバー": [],
            "サイドバー": [],
            "ナビゲーションバー": [],
            "サブメニュー": [],
            "ボタン": [],
            "リンク": [],
            "フォーム": [],
            "テーブル": [],
            "コンテンツ本体": [],
            "その他": []
        }
        
        self.logger.info(f"PageAnalyzerToolを初期化しました (headless: {headless}, output_dir: {self.output_dir})")
        
    def setup(self):
        """ブラウザをセットアップし、必要なツールを初期化する"""
        try:
            # 既存のロガーを渡す（重要！）
            self.browser = Browser(headless=self.headless, logger=self.logger)
            
            # Browserのsetupメソッドを呼び出す
            if not self.browser.setup():
                self.logger.error("ブラウザの初期化に失敗しました")
                return False
            
            # 既存のロガーを渡す（重要！）
            self.page_analyzer = PageAnalyzer(self.browser, logger=self.logger)
            
            # 各種カテゴリーの初期化
            self.categorized_elements = collections.defaultdict(list)
            
            return True
        except Exception as e:
            self._handle_error("ブラウザセットアップ中にエラーが発生しました", e, True)
            return False
            
    def navigate_and_login(self, url=None):
        """ログインしてページに移動"""
        try:
            # ログイン実行
            self.logger.info("ログイン処理を開始します...")
            if not login(self.browser):
                self.logger.error("ログインに失敗しました")
                return False
                
            self.logger.info("ログインに成功しました")
            
            # 特定のURLが指定されていれば移動
            if url:
                self.logger.info(f"指定されたURLに移動します: {url}")
                self.browser.navigate_to(url)
                
                # ページ読み込み待機
                self._wait_for_page_load()
            
            return True
            
        except Exception as e:
            self.logger.error(f"ページへの移動中にエラーが発生しました: {e}")
            self.browser.save_screenshot("navigation_error")
            return False
            
    def analyze_page(self, save_html=True):
        """
        現在のページを分析し、クリック可能な要素や入力フィールドを収集する
        
        Args:
            save_html: HTMLソースを保存するかどうか
            
        Returns:
            dict: 分析結果
        """
        self.logger.info("ページの分析を開始しています...")
        
        result = {
            "success": False,
            "url": self.browser.driver.current_url,
            "title": self.browser.driver.title,
            "html_file": None
        }
        
        try:
            # ページが完全にロードされるまで待機
            self._wait_for_page_load()
            
            # 一連の分析処理を実行
            steps = [
                {"name": "ページ構造解析", "func": self._parse_page_structure},
                {"name": "要素収集", "func": lambda: self._collect_elements("all")},
                {"name": "重複除去", "func": self._remove_duplicates}
            ]
            
            for step in steps:
                try:
                    step["func"]()
                except Exception as e:
                    self._handle_error(f"{step['name']}中にエラーが発生しました", e)
                    # エラーが発生しても次のステップに進む
            
            self.logger.info(f"ページ分析が完了しました（クリック可能: {len(self.clickable_elements)}件、入力: {len(self.input_elements)}件）")
            
            # カテゴリー別の要素数をログに出力
            for category, elements in self.categorized_elements.items():
                if elements:
                    self.logger.info(f"カテゴリー '{category}': {len(elements)}件")
            
            # HTMLソースを保存（オプション）
            html_file = None
            if save_html:
                html_file = self.save_html_source()
                if html_file:
                    self.logger.info(f"HTMLソースを保存しました: {html_file}")
            result["html_file"] = html_file
            
            result["success"] = True
            return result
        
        except Exception as e:
            self._handle_error("ページ分析中に予期しないエラーが発生しました", e, True)
            return result
    
    def _generate_xpath(self, element, text):
        """要素のXPathを生成"""
        return self._generate_unified_xpath(element, text, use_js=False)
            
    def _generate_full_xpath(self, element):
        """要素の完全なXPathを生成（JavaScriptを使用）"""
        return self._generate_unified_xpath(element, use_js=True)
    
    def _generate_unified_xpath(self, element, element_text=None):
        """
        要素のXPathを生成する統合メソッド
        
        Args:
            element: Selenium WebElement
            element_text: 要素のテキスト (オプション)
            
        Returns:
            str: 生成されたXPath
        """
        try:
            # スクリプトを使ってフルXPathを取得
            full_xpath = self.browser.driver.execute_script("""
            function getFullXPath(element) {
                if (!element) return '';
                
                // IDを持つ要素への最適化されたXPath
                if (element.id) {
                    return `//*[@id="${element.id}"]`;
                }
                
                // 子要素を含めるかどうかを判断
                const shouldIncludeChildren = (el) => {
                    if (!el || !el.children) return false;
                    // テキストを持つ子要素や特定のタグを優先
                    for (const child of el.children) {
                        if (child.textContent && child.textContent.trim()) return true;
                        if (['div', 'span', 'img'].includes(child.tagName.toLowerCase())) return true;
                    }
                    return false;
                };
                
                let path = [];
                let current = element;
                
                // 階層を上に辿る
                while (current && current.nodeType === Node.ELEMENT_NODE) {
                    // current要素のインデックスを計算
                    let index = 0;
                    let sibling = current;
                    
                    // 同じ階層の同じタグ名の要素をカウント
                    while (sibling) {
                        if (sibling.nodeName === current.nodeName) {
                            index++;
                        }
                        sibling = sibling.previousElementSibling;
                    }
                    
                    // ノード名とインデックスを使用
                    const tagName = current.nodeName.toLowerCase();
                    let pathSegment = '';
                    
                    // IDがある場合はIDを優先
                    if (current.id) {
                        pathSegment = `//*[@id="${current.id}"]`;
                        path.unshift(pathSegment);
                        break; // IDがあれば探索終了
                    } else {
                        // 同階層に同じタグが複数ある場合はインデックスを付加
                        let siblings = Array.from(current.parentNode?.children || [])
                            .filter(s => s.nodeName === current.nodeName);
                        
                        if (siblings.length > 1) {
                            pathSegment = `/${tagName}[${index}]`;
                        } else {
                            pathSegment = `/${tagName}`;
                        }
                    }
                    
                    path.unshift(pathSegment);
                    
                    // 最も浅い要素（元の要素）かつ子要素を持つ場合
                    if (path.length === 1 && shouldIncludeChildren(current)) {
                        // 特に重要な子要素（テキストを持つ、またはdiv/span）があれば追加
                        for (const child of current.children) {
                            if (child.textContent && child.textContent.trim() || 
                                ['div', 'span'].includes(child.tagName.toLowerCase())) {
                                path.push(`/${child.tagName.toLowerCase()}`);
                                break;
                            }
                        }
                    }
                    
                    current = current.parentNode;
                    
                    // bodyに到達したらそれ以上辿らない（XPathを短くするため）
                    if (current && (current.nodeName === 'BODY' || current.nodeName === 'HTML')) {
                        break;
                    }
                }
                
                // "//"ではじめて絶対パスにする
                if (path.length > 0 && !path[0].startsWith('//*[@id=')) {
                    return '//' + path.join('');
                }
                
                return path.join('');
            }
            
            return getFullXPath(arguments[0]);
            """, element)
            
            # JavaScript生成のXPathが有効なら使用
            if full_xpath and full_xpath.strip():
                return full_xpath
                
            # テキストで検索
            if element_text and element_text.strip():
                # テキストを含む要素を検索するXPath
                safe_text = element_text.replace("'", "\\'")
                text_xpath = f"//*[contains(text(), '{safe_text}')]"
                
                # テキストが完全一致の場合は完全一致条件を使用
                if element.text.strip() == element_text.strip():
                    exact_xpath = f"//*[text()='{safe_text}']"
                    return exact_xpath
                    
                return text_xpath
                
            # フォールバック：PythonでXPathを生成
            from selenium.webdriver.common.by import By
            
            # IDがあればIDで検索
            element_id = element.get_attribute("id")
            if element_id and element_id.strip():
                id_xpath = f"//*[@id='{element_id}']"
                
                # 子要素があれば追加（特に子要素がdivタグの場合）
                try:
                    children = element.find_elements(By.XPATH, "./*")
                    for child in children:
                        if child.tag_name == "div":
                            return f"{id_xpath}/{child.tag_name}"
                except:
                    pass
                    
                return id_xpath
                
            # 階層構造を使ったXPath
            try:
                # 親要素を取得
                parent = element.find_element(By.XPATH, "./..")
                parent_id = parent.get_attribute("id")
                
                if parent_id:
                    # 兄弟要素の中でのインデックスを取得
                    siblings = parent.find_elements(By.XPATH, f"./{element.tag_name}")
                    
                    if len(siblings) > 1:
                        # インデックスを特定
                        for i, sibling in enumerate(siblings, 1):
                            try:
                                if sibling.id == element.id:  # 同じ要素か確認
                                    # 子要素があれば追加
                                    children = element.find_elements(By.XPATH, "./*")
                                    if children and children[0].tag_name == "div":
                                        return f"//*[@id='{parent_id}']/{element.tag_name}[{i}]/{children[0].tag_name}"
                                    return f"//*[@id='{parent_id}']/{element.tag_name}[{i}]"
                            except:
                                continue
                                
                    # 子要素を確認
                    children = element.find_elements(By.XPATH, "./*")
                    if children and children[0].tag_name == "div":
                        return f"//*[@id='{parent_id}']/{element.tag_name}/{children[0].tag_name}"
                        
                    return f"//*[@id='{parent_id}']/{element.tag_name}"
            except:
                # 親要素取得に失敗した場合はタグ名のみのXPathを返す
                pass
                
            # 属性ベースのXPath
            for attr in ["data-rb-event-key", "data-testid", "role", "name", "class"]:
                value = element.get_attribute(attr)
                if value and value.strip():
                    # 特殊文字をエスケープ
                    value = value.replace("'", "\\'")
                    xpath = f"//{element.tag_name}[@{attr}='{value}']"
                    
                    # 子要素を確認
                    try:
                        children = element.find_elements(By.XPATH, "./*")
                        if children and children[0].tag_name == "div":
                            return f"{xpath}/{children[0].tag_name}"
                    except:
                        pass
                        
                    return xpath
                    
            # 最低限のXPath（タグ名のみ）
            return f"//{element.tag_name}"
            
        except Exception as e:
            self.logger.debug(f"XPath生成エラー: {e}")
            return ""
    
    def _parse_page_structure(self):
        """ページ全体の構造を解析（汎用的な実装）"""
        try:
            self.logger.info("ページ構造を解析しています...")
            
            # トップバーの検出
            top_bar_candidates = [
                "#top-bar", 
                "header", 
                ".navbar", 
                ".header",
                "[role='banner']",
                "nav.navbar"
            ]
            
            for selector in top_bar_candidates:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.page_structure["top_bar"] = elements[0]
                        self.logger.info(f"トップバー検出: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"トップバー検索エラー: {e}")
            
            # サイドバーの検出
            sidebar_candidates = [
                "#navbar", 
                ".sidebar", 
                "#sidebar", 
                ".sidenav",
                ".menu-nav",
                ".side-menu"
            ]
            
            for selector in sidebar_candidates:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.page_structure["side_bar"] = elements[0]
                        self.logger.info(f"サイドバー検出: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"サイドバー検索エラー: {e}")
            
            # メインコンテンツの検出
            content_candidates = [
                "main", 
                "#content", 
                ".content", 
                "[role='main']",
                ".main-content",
                ".container"
            ]
            
            for selector in content_candidates:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.page_structure["main_content"] = elements[0]
                        self.logger.info(f"メインコンテンツ検出: {selector}")
                    break
                except Exception as e:
                    self.logger.debug(f"メインコンテンツ検索エラー: {e}")
            
            # ナビゲーションの検出
            nav_candidates = [
                "nav", 
                "[role='navigation']", 
                ".navigation",
                ".nav-container"
            ]
            
            for selector in nav_candidates:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.page_structure["navigation"] = elements[0]
                        self.logger.info(f"ナビゲーション検出: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"ナビゲーション検索エラー: {e}")
            
            self.logger.info("ページ構造解析が完了しました")
            
        except Exception as e:
            self.logger.error(f"ページ構造解析中にエラーが発生: {e}")
    
    def _determine_element_category(self, element, tag_name, attrs, text):
        """要素のカテゴリーを判定"""
        try:
            # 特定の既知要素との照合（詳細分析、データエクスポートなど）
            full_xpath = attrs.get("full_xpath", "")
            if full_xpath in self.special_item_xpath_map:
                return self.special_item_xpath_map[full_xpath]["category"]
            
            # コンテナタイプに基づく判定
            container_type = attrs.get("container_type", "unknown")
            if container_type == "top_bar":
                return "トップバー"
            elif container_type == "side_bar":
                return "サイドバー"
            elif container_type == "navigation":
                return "ナビゲーションバー"
            
            # クラス名とID名からカテゴリーを推定
            class_name = attrs.get("class", "").lower()
            id_name = attrs.get("id", "").lower()
            
            # メニュー項目の判定
            if "menu-item" in class_name or "menu-nav" in class_name or "menu-item" in id_name:
                # 親要素の情報からサブメニューかどうかを判断
                parent_info = attrs.get("parent", {})
                parent_class = parent_info.get("className", "").lower()
                if "submenu" in parent_class or "sub-menu" in parent_class or "dropdown" in parent_class:
                    return "サブメニュー"
                return "サイドバー"
            
            # ナビゲーションバー関連
            if ("nav" in class_name or "nav" in id_name or 
                "header" in class_name or "header" in id_name or
                "menu" in class_name or "menu" in id_name):
                if "top" in class_name or "header" in class_name or "main-nav" in class_name:
                    return "トップバー"
                elif "sub" in class_name or "sub" in id_name:
                    return "サブメニュー"
                elif "side" in class_name or "side" in id_name:
                    return "サイドバー"
                else:
                    return "ナビゲーションバー"
            
            # サイドバー関連
            if ("sidebar" in class_name or "sidebar" in id_name or
                "side-bar" in class_name or "side-bar" in id_name or
                "sidenav" in class_name or "sidenav" in id_name):
                return "サイドバー"
            
            # テーブル関連
            if (tag_name == "table" or "table" in class_name or "table" in id_name or
                tag_name == "tr" or tag_name == "td" or tag_name == "th"):
                return "テーブル"
                
            # フォーム関連
            if (tag_name == "form" or "form" in class_name or "form" in id_name or
                tag_name == "input" or tag_name == "select" or tag_name == "textarea"):
                return "フォーム"
            
            # ボタン関連
            if (tag_name == "button" or "btn" in class_name or "button" in class_name or
                "submit" in class_name or "btn" in id_name):
                return "ボタン"
                
            # リンク関連
            if tag_name == "a":
                # 親要素の情報からカテゴリーを判断
                parent_info = attrs.get("parent", {})
                parent_class = parent_info.get("className", "").lower()
                
                if "menu" in parent_class:
                    return "サイドバー"
                elif "navbar" in parent_class or "nav" in parent_class or "header" in parent_class:
                    return "トップバー"
                else:
                    return "リンク"
                
            # コンテンツ本体関連
            if ("content" in class_name or "content" in id_name or
                "main" in class_name or "main" in id_name or
                "body" in class_name or "body" in id_name):
                return "コンテンツ本体"
            
            # 要素の位置からカテゴリー推定
            location = attrs.get("location", {})
            if location:
                x = location.get("x", 0)
                y = location.get("y", 0)
                
                # 画面上部のものはトップバーの可能性
                if y < 100:
                    return "トップバー"
                # 画面左側のものはサイドバーの可能性
                elif x < 200:
                    return "サイドバー"
            
            # デフォルトカテゴリー
            return "その他"
            
        except Exception as e:
            self.logger.debug(f"カテゴリー判定中にエラーが発生しました: {e}")
            return "その他"
    
    def print_element_tables(self):
        """収集した要素をテーブル形式で表示"""
        # クリック可能な要素を表示
        if self.elements["clickable"]:
            data = [e.as_dict() for e in self.elements["clickable"]]
            df = pd.DataFrame(data)
            
            print("\n=== クリック可能な要素 ===")
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=True))
        
        # 入力フィールドを表示
        if self.elements["input"]:
            data = [e.as_dict() for e in self.elements["input"]]
            df = pd.DataFrame(data)
            
            print("\n=== 入力フィールド ===")
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=True))
        
        # カテゴリー別に要素を表示
        for category, elements in self.categorized_elements.items():
            if elements:
                data = [e.as_dict() for e in elements]
            df = pd.DataFrame(data)
            
            print(f"\n=== {category} ===")
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=True))
    
    def print_category_summary(self):
        """カテゴリー別の要素数をサマリー表示"""
        print("\n=== カテゴリー別要素数 ===")
        data = []
        for category, elements in self.categorized_elements.items():
            data.append({"カテゴリー": category, "要素数": len(elements)})
        
        df = pd.DataFrame(data)
        print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))

    def collect_selectors(self):
        """
        すべてのセレクタ情報を標準化された形式で収集
        
        Returns:
            list: セレクタのリスト（各セレクタは辞書）
        """
        selectors = []
        
        # クリック可能な要素からセレクタを収集
        for i, element in enumerate(self.elements["clickable"]):
            try:
                element_selectors = element.get_selectors()
                name = f"clickable_{i+1}"
                
                # テキスト値を取得
                text_value = element.text
                
                # データ属性を取得
                data_attributes = {}
                for key, value in element.attrs.items():
                    if key.startswith("data-"):
                        data_attributes[key] = value
                
                # セレクタ情報を作成
                selector_info = {
                    "group": "detailed_analysis",
                    "name": name,
                    "text_value": text_value,
                    "id": element_selectors.get("id", ""),
                    "class": element_selectors.get("class", ""),
                    "css": element_selectors.get("css", ""),
                    "xpath": element_selectors.get("xpath", ""),
                    "full_xpath": element_selectors.get("full_xpath", ""),
                    "element_type": "クリック可能",
                    "category": element.category
                }
                
                # データ属性があれば追加
                for key, value in data_attributes.items():
                    # キーからdata-プレフィックスを削除してキャメルケースに変換
                    clean_key = key.replace("data-", "").replace("-", "_")
                    selector_info[clean_key] = value
                
                # 信頼性の高いセレクタを取得
                reliable_selectors = element_selectors.get("reliable_selectors", [])
                selector_info["reliable_selectors"] = reliable_selectors
                
                selectors.append(selector_info)
                
            except Exception as e:
                self.logger.warning(f"セレクタ情報の収集中にエラーが発生しました: {e}")
        
        # 入力フィールドのセレクタ情報も収集
        for i, element in enumerate(self.elements["input"]):
            try:
                element_selectors = element.get_selectors()
                name = f"input_{i+1}"
                
                # 要素の値またはプレースホルダーをテキスト値として使用
                text_value = element.attrs.get("value", "") or element.attrs.get("placeholder", "")
                
                # セレクタ情報を作成
                selector_info = {
                    "group": "detailed_analysis",
                    "name": name,
                    "text_value": text_value,
                    "id": element_selectors.get("id", ""),
                    "class": element_selectors.get("class", ""),
                    "css": element_selectors.get("css", ""),
                    "xpath": element_selectors.get("xpath", ""),
                    "full_xpath": element_selectors.get("full_xpath", ""),
                    "element_type": "入力フィールド",
                    "category": element.category,
                    "field_type": element.attrs.get("type", "")
                }
                
                # 信頼性の高いセレクタを取得
                reliable_selectors = element_selectors.get("reliable_selectors", [])
                selector_info["reliable_selectors"] = reliable_selectors
                
                selectors.append(selector_info)
                
            except Exception as e:
                self.logger.warning(f"入力フィールドのセレクタ情報収集中にエラーが発生しました: {e}")
        
        return selectors
    
    def export_selectors(self, selectors, csv_filename=None, json_filename=None):
        """
        セレクタ情報をCSVとJSONファイルに出力
        
        Args:
            selectors: 出力するセレクタのリスト
            csv_filename: CSV出力ファイル名
            json_filename: JSON出力ファイル名
            
        Returns:
            bool: 出力が成功したかどうか
        """
        success = True
        
        # 出力ディレクトリの存在確認
        os.makedirs(self.output_dir, exist_ok=True)
        
        # CSV出力
        if csv_filename:
            if not self.export_selectors_to_csv(selectors, csv_filename):
                success = False
        
        # JSON出力
        if json_filename:
            if not self.export_selectors_to_json(selectors, json_filename):
                success = False
        
        return success
    
    def export_selectors_to_csv(self, selectors=None, filename=None):
        """
        収集したセレクタをCSVファイルとしてエクスポート
        
        Args:
            selectors: エクスポートするセレクタ情報のリスト
            filename: 出力ファイル名
        """
        if not selectors:
            selectors = self.collect_selectors()
            
        if not selectors:
            self.logger.warning("エクスポートするセレクタがありません")
            return
            
        # 出力ファイル名の決定
        if not filename:
            output_dir = self.output_dir or os.path.join(os.getcwd(), "data", "page_analyze")
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, "selectors_analysis.csv")
            
        try:
            # CSVファイルに書き出し
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # 必須フィールドの設定
                fieldnames = [
                    'group', 'name', 'text_value', 'id', 'class', 'css', 'xpath', 
                    'full_xpath', 'element_type', 'category'
                ]
                
                # オプションフィールドの追加（各セレクタから動的に収集）
                optional_fields = set()
                for selector in selectors:
                    for key in selector.keys():
                        if key not in fieldnames and key != 'reliable_selectors':
                            optional_fields.add(key)
                
                # フィールド名を結合
                fieldnames.extend(sorted(optional_fields))
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                
                # セレクタデータの書き込み
                for selector in selectors:
                    # CSVで問題になる特殊文字の処理
                    row_data = {}
                    for key, value in selector.items():
                        if key == 'reliable_selectors':
                            continue  # セレクタリストはCSVに含めない
                            
                        if key in ['xpath', 'full_xpath'] and value:
                            # XPathのダブルクォーテーションがエスケープされている場合、一つだけ残す
                            # ただし、CSVでは引用符で囲まれるのでバックスラッシュは1つだけ必要
                            value = value.replace('\\"', '"')
                            
                        if isinstance(value, str):
                            # 改行をスペースに置換
                            value = value.replace("\n", " ")
                        
                        row_data[key] = value
                        
                    writer.writerow(row_data)
                
            self.logger.info(f"セレクタ情報をCSVファイルにエクスポートしました: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"CSVエクスポート中にエラーが発生しました: {e}")
            return None

    def export_selectors_to_json(self, selectors=None, filename=None):
        """
        収集したセレクタをJSONファイルとしてエクスポート
        
        Args:
            selectors: エクスポートするセレクタ情報のリスト
            filename: 出力ファイル名
            
        Returns:
            str: 出力ファイルのパス、または失敗時にNone
        """
        if not selectors:
            selectors = self.collect_selectors()
            
        if not selectors:
            self.logger.warning("エクスポートするセレクタがありません")
            return
            
        # 出力ファイル名の決定
        if not filename:
            output_dir = self.output_dir or os.path.join(os.getcwd(), "data", "page_analyze")
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, "selectors_analysis.json")
            
        try:
            # XPathのダブルクォーテーションの修正
            for selector in selectors:
                for key in ['xpath', 'full_xpath']:
                    if key in selector and selector[key]:
                        # XPathのダブルクォーテーションが重複しないように修正
                        selector[key] = selector[key].replace('\\"', '"')
                        
                # reliable_selectorsのXPathも修正
                if 'reliable_selectors' in selector:
                    for reliable in selector['reliable_selectors']:
                        if reliable['type'] == 'xpath' and reliable['value']:
                            reliable['value'] = reliable['value'].replace('\\"', '"')
            
            # JSONファイルに書き出し
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(selectors, jsonfile, ensure_ascii=False, indent=2)
                
            self.logger.info(f"セレクタ情報をJSONファイルにエクスポートしました: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"JSONエクスポート中にエラーが発生しました: {e}")
            return None
    
    def save_html_source(self, filename=None, html_dir=None):
        """
        現在のページのHTMLソースを保存する
        
        Args:
            filename (str, optional): 保存するファイル名。指定しない場合はタイムスタンプを含む名前を生成
            html_dir (str, optional): HTML保存先ディレクトリ。指定しない場合はself.output_dir内のhtmlディレクトリを使用
            
        Returns:
            str or None: 保存したファイルのパス。失敗した場合はNone
        """
        try:
            if not self.browser or not self.browser.driver:
                self.logger.error("ブラウザが初期化されていません")
                return None
                
            # 出力ディレクトリの設定
            if not html_dir:
                html_dir = os.path.join(self.output_dir, "html")
            
            # ディレクトリの存在確認と作成
            os.makedirs(html_dir, exist_ok=True)
            
            # 現在のURLを取得して、ファイル名に使用するための安全な文字列に変換
            current_url = self.browser.driver.current_url
            url_part = ""
            try:
                # URLからドメイン部分を抽出
                from urllib.parse import urlparse
                parsed_url = urlparse(current_url)
                url_part = parsed_url.netloc
                
                # パス部分も追加（必要に応じて）
                if parsed_url.path and parsed_url.path != "/":
                    # パスから不正なファイル名文字を除去
                    path_part = parsed_url.path.strip("/").replace("/", "_")
                    path_part = "".join(c for c in path_part if c.isalnum() or c in "_-.")
                    if path_part:
                        url_part = f"{url_part}_{path_part[:30]}"  # 長すぎるパスは切り詰め
            except Exception as url_e:
                self.logger.debug(f"URL解析中にエラーが発生しました: {url_e}")
                # エラーが発生しても処理を継続
                url_part = "page"
            
            # ファイル名の生成
            if not filename:
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{url_part}_{now_str}.html"
            
            # ファイルパスの作成
            file_path = os.path.join(html_dir, filename)
            
            # HTMLソースの取得
            html_source = self.browser.get_page_source()
            if not html_source:
                self.logger.error("HTMLソースの取得に失敗しました")
                return None
            
            # HTMLソースをファイルに保存
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_source)
                
            self.logger.info(f"HTMLソースを保存しました: {file_path}")
            return file_path
            
        except PermissionError:
            self._handle_error(f"HTMLファイルへの書き込み権限がありません: {filename}", "PermissionError")
            return None
        except FileNotFoundError:
            self._handle_error(f"HTMLファイルの出力先パスが存在しません", "FileNotFoundError")
            return None
        except Exception as e:
            self._handle_error("HTMLソースの保存中にエラーが発生しました", e, True)
            return None
    
    def _collect_clickable_elements(self):
        """クリック可能な要素を収集"""
        return self._collect_elements("clickable")

    def _collect_input_elements(self):
        """入力フィールドを収集"""
        return self._collect_elements("input")

    def _collect_elements(self, element_type="all"):
        """
        ページ上の要素を収集する統合メソッド
        
        Args:
            element_type: 収集する要素タイプ
                "clickable": クリック可能な要素
                "input": 入力フィールド
                "all": すべてのインタラクティブな要素
                
        Returns:
            list: 収集された要素のリスト
        """
        collected_elements = []
        
        try:
            # 検索セレクタの定義
            selectors_map = {
                "clickable": [
                    "a", "button", 
                    "input[type='button']", "input[type='submit']", 
                    "[role='button']", ".btn", "[onclick]",
                    "input[type='checkbox']", "input[type='radio']"
                ],
                "input": [
                    "input:not([type='hidden'])",
                    "textarea",
                    "select"
                ]
            }
            
            # 処理対象のエレメントタイプを決定
            element_types = ["clickable", "input"] if element_type == "all" else [element_type]
            
            # 各タイプに対して要素収集
            for elem_type in element_types:
                if elem_type not in selectors_map:
                    continue
                
                for selector in selectors_map[elem_type]:
                    try:
                        elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            try:
                                # 基本的な要素情報を収集
                                info = self._collect_element_info(element, elem_type)
                                if info and info.attrs.get("is_displayed") and info.attrs.get("is_enabled"):
                                    collected_elements.append(info)
                                    
                                    # 要素タイプに応じたリストに追加
                                    self.elements[elem_type].append(info)
                                    
                                    # カテゴリー決定と分類
                                    if elem_type == "clickable":
                                        category = self._determine_element_category(
                                            element, 
                                            info.tag, 
                                            info.attrs, 
                                            info.text
                                        )
                                    else:
                                        category = "フォーム"
                                        
                                    self.categorized_elements[category].append(info)
                                    
                            except Exception as e:
                                self.logger.debug(f"要素処理中にエラー: {e}")
                                
                    except Exception as e:
                        self.logger.debug(f"セレクタ '{selector}' の探索中にエラー: {e}")
        
            # 要素タイプ別のカウントをログに記録
            if element_type == "clickable":
                self.logger.info(f"クリック可能要素を {len(self.elements['clickable'])} 件収集しました")
            elif element_type == "input":
                self.logger.info(f"入力フィールドを {len(self.elements['input'])} 件収集しました")
            else:
                self.logger.info(f"インタラクティブ要素を {len(collected_elements)} 件収集しました")
                
            return collected_elements
            
        except Exception as e:
            self.logger.error(f"要素収集中にエラーが発生しました: {e}")
            return []
            
    def _collect_element_info(self, element, element_type):
        """
        要素の詳細情報を収集する
        
        Args:
            element: Selenium WebElement
            element_type: 要素タイプ（"clickable"または"input"）
            
        Returns:
            ElementInfo: 収集された要素情報
        """
        try:
            tag_name = element.tag_name
            element_id = element.get_attribute("id") or ""
            element_name = element.get_attribute("name") or ""
            element_class = element.get_attribute("class") or ""
            
            # 要素タイプに応じて追加情報を収集
            if element_type == "clickable":
                element_text = element.text or element.get_attribute("value") or ""
                element_type_attr = element.get_attribute("type") or ""
                element_role = element.get_attribute("role") or ""
                
                # 要素の表示・有効状態を確認
                is_displayed = element.is_displayed()
                is_enabled = element.is_enabled()
                
                # XPathとCSSセレクタを生成
                xpath = self._generate_unified_xpath(element, element_text)
                # full_xpathの生成 - 子要素を含む詳細なパスを生成
                full_xpath = self._generate_unified_xpath(element, element_text)
                css_path = self._generate_unified_css_selector(element)
                
                # 要素の位置情報を取得
                try:
                    location = element.location
                    size = element.size
                    element_location = {
                        "x": location["x"],
                        "y": location["y"],
                        "width": size["width"],
                        "height": size["height"]
                    }
                except:
                    element_location = {}
                
                # ElementInfoオブジェクトを作成
                element_info = ElementInfo(
                    element=element,
                    tag=tag_name,
                    text=element_text,
                    attrs={
                        "id": element_id,
                        "name": element_name,
                        "class": element_class,
                        "type": element_type_attr,
                        "role": element_role,
                        "is_displayed": is_displayed,
                        "is_enabled": is_enabled,
                        "xpath": xpath,
                        "full_xpath": full_xpath,
                        "css_path": css_path,
                        "location": element_location
                    },
                    category="未分類"  # カテゴリは後で_determine_element_categoryで決定
                )
                
                return element_info
                
            elif element_type == "input":
                element_type_attr = element.get_attribute("type") or tag_name
                element_value = element.get_attribute("value") or ""
                element_placeholder = element.get_attribute("placeholder") or ""
                is_displayed = element.is_displayed()
                is_enabled = element.is_enabled()
                
                # XPathとCSSセレクタを生成
                xpath = self._generate_unified_xpath(element)
                # full_xpathの生成 - 子要素を含む詳細なパスを生成
                full_xpath = self._generate_unified_xpath(element)
                css_path = self._generate_unified_css_selector(element)
                
                # 要素の位置情報を取得
                try:
                    location = element.location
                    size = element.size
                    element_location = {
                        "x": location["x"],
                        "y": location["y"],
                        "width": size["width"],
                        "height": size["height"]
                    }
                except:
                    element_location = {}
                
                # ElementInfoオブジェクトを作成
                element_info = ElementInfo(
                    element=element,
                    tag=tag_name,
                    text=element_value or element_placeholder,
                    attrs={
                        "id": element_id,
                        "name": element_name,
                        "class": element_class,
                        "type": element_type_attr,
                        "value": element_value,
                        "placeholder": element_placeholder,
                        "is_displayed": is_displayed,
                        "is_enabled": is_enabled,
                        "xpath": xpath,
                        "full_xpath": full_xpath,
                        "css_path": css_path,
                        "location": element_location
                    },
                    category="フォーム"
                )
                
                return element_info
                
        except Exception as e:
            self.logger.debug(f"要素情報収集中にエラー: {e}")
            return None

    def _remove_duplicates(self):
        """重複する要素を削除"""
        # 各要素リストから重複を排除
        for key in self.elements:
            unique_elements = []
            seen_ids = set()
            seen_xpaths = set()
            
            for element in self.elements[key]:
                # 要素のIDまたはXPathを取得
                element_id = None
                element_xpath = None
                
                # IDによる重複チェック
                if hasattr(element.element, "id"):
                    element_id = element.element.id
                elif element.attrs.get("id"):
                    element_id = element.attrs.get("id")
                
                # XPathによる重複チェック
                element_xpath = element.attrs.get("xpath")
                
                # ID、XPath、テキスト＋タグの組み合わせで重複チェック
                is_duplicate = False
                if element_id and element_id in seen_ids:
                    is_duplicate = True
                elif element_xpath and element_xpath in seen_xpaths:
                    is_duplicate = True
                else:
                    # IDとXPath以外の場合は、テキストとタグの組み合わせで重複チェック
                    for existing in unique_elements:
                        if (existing.tag == element.tag and
                            existing.text == element.text and
                            existing.attrs.get("location") == element.attrs.get("location")):
                            is_duplicate = True
                            break
                
                # 重複でなければリストに追加
                if not is_duplicate:
                    if element_id:
                        seen_ids.add(element_id)
                    if element_xpath:
                        seen_xpaths.add(element_xpath)
                    unique_elements.append(element)
            
            # 重複排除後のリストで更新
            self.elements[key] = unique_elements
            
        # clickable_elementsとinput_elementsも更新
        self.clickable_elements = self.elements["clickable"]
        self.input_elements = self.elements["input"]

    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            try:
                self.logger.info("ブラウザを終了します...")
                self.browser.quit()
            except Exception as e:
                self.logger.warning(f"ブラウザの終了に失敗しました: {e}")
    
    def find_element_selector(self, text, element_types=None, exact_match=False, category=None, group_name="common"):
        """
        テキストを含む要素を検索し、クリックに最適なセレクタを取得する
        
        Args:
            text (str): 検索するテキスト
            element_types (list): 検索対象の要素タイプ (例: ['a', 'button', 'div'])
            exact_match (bool): 完全一致で検索するかどうか
            category (str): 要素カテゴリー (例: "navigation", "button")
            group_name (str): セレクタのグループ名
            
        Returns:
            dict: 要素の情報とセレクタ
                - element: 見つかった要素
                - selectors: 推奨セレクタの辞書
                - tag: 要素のタグ名
                - attributes: 要素の属性
        """
        self.logger.info(f"「{text}」を含む要素を検索しています...")
        
        try:
            # デフォルトの要素タイプ
            if element_types is None:
                element_types = ['a', 'button', 'div', 'span', 'li', 'input']
            
            # 検索方法の優先順位付き実行
            search_methods = [
                {
                    "name": "直接検索",
                    "func": lambda: self.browser.find_element_by_text(text, element_types, exact_match),
                    "process": lambda results: {
                        "element": results[0]['element'],
                        "selectors": self._generate_selectors(results[0]['element'], text, group_name),
                        "tag": results[0]['tag'],
                        "attributes": self._get_element_attributes(results[0]['element'])
                    } if results else None
                },
                {
                    "name": "子要素検索",
                    "func": lambda: self.browser.driver.find_elements(
                        By.XPATH, 
                        f"//*//*[contains(text(), '{text}')]/ancestor::*[self::{' or self::'.join(element_types)}][1]"
                    ),
                    "process": lambda results: {
                        "element": results[0],
                        "selectors": self._generate_selectors(results[0], text, group_name),
                        "tag": results[0].tag_name,
                        "attributes": self._get_element_attributes(results[0])
                    } if results else None
                },
                {
                    "name": "React構造検索",
                    "func": lambda: self.browser.driver.find_elements(
                        By.XPATH, 
                        f"//*[.//div[contains(text(), '{text}')]]"
                    ),
                    "process": lambda results: {
                        "element": results[0],
                        "selectors": self._generate_selectors(results[0], text, group_name),
                        "tag": results[0].tag_name,
                        "attributes": self._get_element_attributes(results[0])
                    } if results else None
                }
            ]
            
            # 各検索方法を順に試す
            for method in search_methods:
                try:
                    results = method["func"]()
                    if results:
                        self.logger.info(f"{method['name']}で「{text}」を含む要素を発見しました")
                        return method["process"](results)
                except Exception as e:
                    self.logger.debug(f"{method['name']}中にエラー: {e}")
                    continue
            
            self.logger.warning(f"「{text}」を含む要素が見つかりませんでした")
            return None
                
        except Exception as e:
            self._handle_error(f"要素検索中にエラーが発生しました", e)
            return None
    
    def _generate_selectors(self, element, text, group_name="common"):
        """
        要素に対する最適なセレクタを生成する
        
        Args:
            element: Selenium WebElement
            text: 検索に使用したテキスト
            group_name: セレクタのグループ名
            
        Returns:
            dict: 各種セレクタ情報
        """
        selectors = {
            "by_id": None,
            "by_css": None,
            "by_xpath": None,
            "by_data_attr": None,
            "by_text": None,
            "best": None,  # 最適なセレクタ
            "reliable": None,  # 信頼性の高いセレクタ
            "selector_list": [],  # CSVに追加可能なセレクタのリスト
            "name_base": text.replace(" ", "_").lower()  # セレクタ名のベース
        }
        
        try:
            # ID属性があるかチェック
            element_id = element.get_attribute("id")
            if element_id and element_id.strip():
                selectors["by_id"] = {"type": "id", "value": element_id}
                selectors["best"] = selectors["by_id"]
                selectors["reliable"] = selectors["by_id"]
                selectors["selector_list"].append({
                    "group": group_name,
                    "name": f"{selectors['name_base']}_id",
                    "selector_type": "id",
                    "selector_value": element_id,
                    "description": f"{text}のID"
                })
                
            # データ属性をチェック (React, Angular, Vue.jsなどでよく使用される)
            data_attrs = {}
            for attr in ["data-rb-event-key", "data-testid", "data-id", "data-key", "data-value"]:
                value = element.get_attribute(attr)
                if value:
                    data_attrs[attr] = value
                    
            if data_attrs:
                # 最も信頼性の高いデータ属性を選択
                best_attr = next(iter(data_attrs.items()))
                for attr, value in data_attrs.items():
                    if attr in ["data-testid", "data-rb-event-key"]:
                        best_attr = (attr, value)
                        break
                        
                attr_name, attr_value = best_attr
                css_selector = f"{element.tag_name}[{attr_name}='{attr_value}']"
                selectors["by_data_attr"] = {"type": "css", "value": css_selector}
                
                # IDがない場合はデータ属性を最良とする
                if not selectors["best"]:
                    selectors["best"] = selectors["by_data_attr"]
            
            # XPathを生成
            xpath = self._generate_unified_xpath(element, text)
            if xpath:
                selectors["by_xpath"] = {"type": "xpath", "value": xpath}
                selectors["selector_list"].append({
                    "group": group_name,
                    "name": f"{selectors['name_base']}_xpath",
                    "selector_type": "xpath",
                    "selector_value": xpath,
                    "description": f"{text}のXPath"
                })
                
                # もし最良セレクタがまだ設定されていなければXPathを使用
                if not selectors["best"]:
                    selectors["best"] = selectors["by_xpath"]
            
            # テキストベースのXPathを生成
            if text and text.strip():
                safe_text = text.replace("'", "\\'")
                text_xpath = f"//*[contains(text(), '{safe_text}')]"
                selectors["by_text"] = {"type": "xpath", "value": text_xpath}
                selectors["selector_list"].append({
                    "group": group_name,
                    "name": f"{selectors['name_base']}_text",
                    "selector_type": "xpath",
                    "selector_value": text_xpath,
                    "description": f"{text}を含むテキスト"
                })
                
                # 信頼性が未設定なら、テキストXPathを設定
                if not selectors["reliable"]:
                    selectors["reliable"] = selectors["by_text"]
            
            # CSSセレクタを生成
            css_selector = self._generate_unified_css_selector(element)
            if css_selector:
                selectors["by_css"] = {"type": "css", "value": css_selector}
                selectors["selector_list"].append({
                    "group": group_name,
                    "name": f"{selectors['name_base']}_css",
                    "selector_type": "css",
                    "selector_value": css_selector,
                    "description": f"{text}のCSSセレクタ"
                })
                
                # 最良セレクタとして優先度を設定
                if not selectors["best"]:
                    selectors["best"] = selectors["by_css"]
                    
                # 信頼性高いセレクタが未設定なら、CSSセレクタを設定
                if not selectors["reliable"]:
                    selectors["reliable"] = selectors["by_css"]
            
            # タグ名とインデックスを使用したCSSセレクタ（最後の手段）
            if not selectors["best"]:
                selectors["best"] = {"type": "css", "value": element.tag_name}
            
            return selectors
            
        except Exception as e:
            self.logger.error(f"セレクタ生成中にエラーが発生しました: {e}")
            
            # 最低限のセレクタを返す
            tag_name = getattr(element, "tag_name", "div")
            if not selectors["best"]:
                selectors["best"] = {"type": "css", "value": tag_name}
                
            return selectors
    
    def _get_element_attributes(self, element):
        """要素の全属性を取得する"""
        try:
            script = """
            var attributes = arguments[0].attributes;
            var result = {};
            for (var i = 0; i < attributes.length; i++) {
                var attr = attributes[i];
                result[attr.name] = attr.value;
            }
            return result;
            """
            return self.browser.driver.execute_script(script, element) or {}
        except Exception as e:
            self.logger.error(f"属性の取得中にエラーが発生しました: {e}")
            return {}
    
    def _wait_for_page_load(self, timeout=30):
        """ページの読み込みを待機"""
        try:
            # document.readyStateがcompleteになるまで待機
            WebDriverWait(self.browser.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # DOMの変更が落ち着くのを待つ（JavaScriptの読み込み完了を待機する）
            WebDriverWait(self.browser.driver, 5).until(
                lambda driver: driver.execute_script(
                    "return (typeof jQuery === 'undefined' || jQuery.active === 0) && "
                    "(typeof angular === 'undefined' || !angular.element(document).injector() || "
                    "!angular.element(document).injector().get('$http').pendingRequests.length)"
                )
            )
            
            return True
        except Exception as e:
            self.logger.warning(f"ページ読み込み待機中にエラーが発生しました: {e}")
            return False
    
    def find_all_interactive_elements(self):
        """
        ページ上のすべてのインタラクティブな要素（クリック可能と入力フィールド）を収集
        
        Returns:
            dict: 収集された要素のリスト
        """
        # 統合メソッドを使用して全ての要素を収集
        return self._collect_elements("all")

    def _generate_unified_css_selector(self, element, use_js=True):
        """
        要素のCSSセレクタを生成する統合メソッド
        
        Args:
            element: Selenium WebElement
            use_js: JavaScriptを使用して詳細なCSSセレクタを生成するか
            
        Returns:
            str: 生成されたCSSセレクタ
        """
        try:
            # IDがある場合はIDを使用
            element_id = element.get_attribute("id")
            if element_id and element_id.strip():
                return f"#{element_id}"
                
            # データ属性を確認 - 適切な子要素も含めたセレクタを生成するため、JavaScript関数を常に優先して使用
            if use_js:
                css_path_script = """
                function getCssPath(element) {
                    if (!element) return null;
                    
                    // 直接のIDセレクタをチェック
                    if (element.id) return `#${element.id}`;
                    
                    // 重要な子要素をチェック
                    const hasImportantChild = (el) => {
                        if (!el || !el.children.length === 0) return false;
                        // 子要素の配列を返す
                        const importantChildren = [];
                        for (const child of el.children) {
                            // テキストを持つ子要素や特定のタグを優先
                            if (child.textContent && child.textContent.trim()) {
                                importantChildren.push(child);
                            } else if (['div', 'span', 'img', 'i', 'em', 'strong'].includes(child.tagName.toLowerCase())) {
                                importantChildren.push(child);
                            }
                        }
                        return importantChildren.length > 0 ? importantChildren : false;
                    };
                    
                    // 親要素を含むセレクタを構築
                    const buildPath = (element, includeChild = false) => {
                        if (!element) return '';
                        
                        let path = [];
                        let current = element;
                        let childSelector = '';
                        
                        // 重要な子要素を持つ場合、その子要素をセレクタに含める
                        if (includeChild) {
                            const importantChildren = hasImportantChild(element);
                            if (importantChildren && importantChildren.length > 0) {
                                // 最初の重要な子要素を使用
                                const firstChild = importantChildren[0];
                                childSelector = ` > ${firstChild.tagName.toLowerCase()}`;
                            }
                        }
                        
                        // 5階層の深さを上限に親要素をたどる
                        let depth = 0;
                        const maxDepth = 5;
                        
                        while (current && current.nodeType === 1 && depth < maxDepth) {
                            // ベースセレクタの作成
                            let selector = current.tagName.toLowerCase();
                            
                            // IDがあればそれを利用して階層探索を終了
                            if (current.id) {
                                path.unshift(`#${current.id}`);
                                if (depth === 0 && childSelector) path[0] += childSelector;
                                break;
                            }
                            
                            // 兄弟要素の中での位置を特定（nth-child）
                            // より安定したnth-childを使用する
                            if (current.parentNode) {
                                const children = Array.from(current.parentNode.children);
                                const index = children.indexOf(current) + 1;
                                
                                if (children.length > 1) {
                                    selector += `:nth-child(${index})`;
                                }
                            }
                            
                            // クラスと属性を追加
                            if (current.className && typeof current.className === 'string') {
                                const classes = current.className.trim().split(/\\s+/).filter(Boolean);
                                
                                if (classes.length > 0) {
                                    // 重要なクラスとReact特有のクラスを優先
                                    const significantClasses = classes.filter(c => 
                                        /^(nav|menu|btn|button|tab|header|footer|main|content|row|container|active|selected|primary|navbar)/.test(c)
                                    );
                                    
                                    // data属性を持つ場合は最小限のクラスを使用
                                    const hasDataAttributes = Object.entries(current.attributes).some(([_, attr]) => 
                                        attr.name && attr.name.startsWith('data-')
                                    );
                                    
                                    if (significantClasses.length > 0) {
                                        // 重要なクラスを最大1つだけ追加（セレクタをシンプルに保つ）
                                        selector += `.${significantClasses[0]}`;
                                    } else if (!hasDataAttributes && classes.length > 0) {
                                        // データ属性がなく、クラスがある場合は最初のクラスを使用
                                        selector += `.${classes[0]}`;
                                    }
                                }
                            }
                            
                            // data-rb-event-keyなど重要な属性を追加
                            let attributeAdded = false;
                            for (const attr of ['data-rb-event-key', 'data-testid', 'data-id', 'role', 'name']) {
                                const value = current.getAttribute(attr);
                                if (value && value.trim()) {
                                    const escapedValue = value.replace(/'/g, "\\'");
                                    selector += `[${attr}='${escapedValue}']`;
                                    attributeAdded = true;
                                    break;
                                }
                            }
                            
                            // 最初の要素（元の要素）にchildSelectorを追加
                            if (depth === 0 && childSelector) {
                                selector += childSelector;
                            }
                            
                            path.unshift(selector);
                            current = current.parentNode;
                            depth++;
                            
                            // 親要素にIDがあれば、それをパスの先頭に追加して終了
                            if (current && current.id) {
                                path.unshift(`#${current.id}`);
                                break;
                            }
                        }
                        
                        return path.join(' > ');
                    };
                    
                    // まず子要素を含めたセレクタを試す
                    let selector = buildPath(element, true);
                    
                    // 特別なケース：テキストを含む要素やリンク要素の処理
                    const hasText = element.textContent && element.textContent.trim();
                    const isLinkOrButton = ['a', 'button'].includes(element.tagName.toLowerCase());
                    
                    if ((isLinkOrButton || hasText) && element.children.length > 0) {
                        // 子要素を含めたより具体的なセレクタを生成
                        return buildPath(element, true);
                    }
                    
                    return selector;
                }
                
                try {
                    return getCssPath(arguments[0]);
                } catch (e) {
                    console.error('CSS selector generation error:', e);
                    return null;
                }
                """
                
                try:
                    # JavaScriptを使用してCSSセレクタを生成
                    css_selector = self.browser.driver.execute_script(css_path_script, element)
                    if css_selector:
                        return css_selector
                except Exception as js_error:
                    self.logger.warning(f"JavaScriptでのCSSセレクタ生成に失敗: {js_error}")
            
            # JavaScriptが失敗した場合、Selenium APIを使用してフォールバック
            from selenium.webdriver.common.by import By
            
            # タグ名とクラス名でシンプルなセレクタを構築
            tag_name = element.tag_name
            class_attr = element.get_attribute("class")
            
            # データ属性を確認 - より安定したセレクタのために
            for attr in ["data-rb-event-key", "data-testid", "data-id", "role"]:
                value = element.get_attribute(attr)
                if value and value.strip():
                    # 特殊文字をエスケープ
                    value = value.replace("'", "\\'")
                    return f"{tag_name}[{attr}='{value}']"
            
            if class_attr and class_attr.strip():
                # 意味のあるクラス名を優先
                classes = class_attr.split()
                important_classes = [c for c in classes if re.search(r'^(nav|menu|btn|button|tab|header|footer|main|content|row|col)', c) or 
                                    c in ['active', 'selected', 'primary', 'secondary', 'container']]
                
                if important_classes:
                    # 重要なクラスを最大2つ使用
                    return f"{tag_name}.{'.'.join(important_classes[:2])}"
                else:
                    # 重要でないクラスは1つだけ使用
                    return f"{tag_name}.{classes[0]}"
                
            # 属性を使用したセレクタ（拡張）
            for attr in ["name", "type", "role", "aria-label", "title", "placeholder", "for"]:
                value = element.get_attribute(attr)
                if value and value.strip():
                    # 特殊文字をエスケープ
                    value = value.replace("'", "\\'")
                    return f"{tag_name}[{attr}='{value}']"
                    
            # 階層セレクタの生成を試みる
            try:
                parent = element.find_element(By.XPATH, "./..")
                parent_id = parent.get_attribute("id")
                if parent_id:
                    # 親要素のIDを使用
                    siblings = parent.find_elements(By.XPATH, f"./{tag_name}")
                    if len(siblings) > 1:
                        # 同じタグの兄弟要素がある場合はインデックスを使用
                        for i, sibling in enumerate(siblings, 1):
                            if sibling.id == element.id:
                                return f"#{parent_id} > {tag_name}:nth-child({i})"
                    return f"#{parent_id} > {tag_name}"
            except:
                pass
                
            # 最低限のセレクタ
            return tag_name
            
        except Exception as e:
            self.logger.debug(f"CSSセレクタ生成エラー: {e}")
            return ""

    def _handle_error(self, error_msg, e, traceback_log=False):
        """共通のエラー処理ロジック
        
        Args:
            error_msg: エラーメッセージの前半部分
            e: 例外オブジェクト
            traceback_log: トレースバックを詳細ログに出力するかどうか
            
        Returns:
            bool: 常にFalse（エラー発生を示す）
        """
        self.logger.error(f"{error_msg}: {e}")
        
        if traceback_log:
            import traceback
            self.logger.debug(f"詳細エラー: {traceback.format_exc()}")
        
        return False


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description="ページ解析ツール")
    parser.add_argument('--headless', help='ヘッドレスモードで実行', action='store_true')
    parser.add_argument('--url', help='分析するURL', type=str, default=None)
    parser.add_argument('--output', help='セレクタ出力ファイル名（非推奨、--csv-output を使用してください）', default="selectors_analysis.csv")
    parser.add_argument('--csv-output', help='CSVセレクタ出力ファイル名')
    parser.add_argument('--json-output', help='JSONセレクタ出力ファイル名')
    parser.add_argument('--output-dir', help='出力ディレクトリ', default=OUTPUT_DIR)
    parser.add_argument('--save-html', help='HTMLソースを保存する', action='store_true', default=True)
    parser.add_argument('--no-save-html', help='HTMLソースを保存しない', dest='save_html', action='store_false')
    parser.add_argument('--find-all-elements', help='ページ上の全てのインタラクティブ要素（クリック可能要素・入力要素）を検索・抽出する', action='store_true')
    parser.add_argument('--find-element', help='指定したテキストを含む要素を検索する', type=str)
    parser.add_argument('--element-types', help='検索対象の要素タイプ（カンマ区切り、例: a,button,div）', type=str, default='a,button,div,span')
    parser.add_argument('--exact-match', help='完全一致で検索する', action='store_true')
    parser.add_argument('--group-name', help='セレクタのグループ名', type=str, default='common')
    
    return parser.parse_args()


def main():
    """メイン処理"""
    # コマンドライン引数を解析
    args = parse_args()
    
    # 出力ディレクトリが存在することを確認
    os.makedirs(args.output_dir, exist_ok=True)
    
    # ページ解析ツールのインスタンスを作成
    analyzer = PageAnalyzerTool(
        headless=args.headless,
        output_dir=args.output_dir
    )
    
    try:
        # ブラウザをセットアップ
        if not analyzer.setup():
            logger.error("ブラウザのセットアップに失敗しました")
            return 1
            
        # ログインしてページに移動
        if not analyzer.navigate_and_login(url=args.url):
            logger.error("ログインまたはページ移動に失敗しました")
            return 1
        
        # 要素検索オプションの処理
        search_performed = False
        
        # 任意の要素を検索する場合
        if args.find_element:
            search_performed = True
            logger.info(f"「{args.find_element}」要素の検索を実行します...")
            
            # 要素タイプのリストを作成
            element_types = args.element_types.split(',')
            
            # 要素を検索
            result = analyzer.find_element_selector(
                text=args.find_element,
                element_types=element_types,
                exact_match=args.exact_match,
                group_name=args.group_name
            )
            
            if result:
                print("\n===== 検索結果 =====")
                print(f"検索テキスト: {args.find_element}")
                print(f"タグ: {result['tag']}")
                
                # 最適なセレクタ
                if result["selectors"]["best"]:
                    best_type = result["selectors"]["best"]["type"]
                    best_value = result["selectors"]["best"]["value"]
                    print(f"\n最適なセレクタ: {best_type}={best_value}")
                
                # 信頼性の高いセレクタ
                if result["selectors"]["reliable"]:
                    reliable_type = result["selectors"]["reliable"]["type"]
                    reliable_value = result["selectors"]["reliable"]["value"]
                    print(f"信頼性の高いセレクタ: {reliable_type}={reliable_value}")
                
                # データ属性（React, Angular用）
                data_attrs = result["attributes"].get("data_attributes", {})
                if data_attrs:
                    print("\n--- データ属性 ---")
                    for attr, value in data_attrs.items():
                        print(f"{attr}: {value}")
                
                # CSVで使用できるセレクタのリスト
                print("\n--- CSVで使用できるセレクタ ---")
                for selector in result["selectors"]["selector_list"]:
                    print(f"{selector['group']},{selector['name']},{selector['selector_type']},{selector['selector_value']},{selector['description']}")
            else:
                logger.error(f"「{args.find_element}」を含む要素が見つかりませんでした")
        
        # 全インタラクティブ要素を検索
        if args.find_all_elements:
            search_performed = True
            logger.info("ページ上の全てのインタラクティブ要素を検索します...")
            elements = analyzer.find_all_interactive_elements()
            
            if elements:
                print("\n===== ページ上のインタラクティブ要素情報 =====")
                clickable_count = len([e for e in elements if e.tag in ['a', 'button', 'input'] or 'click' in str(e.attrs.get('class', '')).lower()])
                input_count = len([e for e in elements if e.attrs.get('type') in ['text', 'email', 'password', 'textarea', 'select']])
                print(f"クリック可能要素数: {clickable_count}")
                print(f"入力要素数: {input_count}")
                print(f"要素数: {len(elements)}")
                
                # セレクタリストをPageAnalyzerToolの形式に変換
                converted_selectors = []
                for i, element in enumerate(elements):
                    selectors = element.get_selectors()
                    element_type = "クリック可能" if element.tag in ['a', 'button'] else "入力フィールド"
                    
                    converted_selectors.append({
                        "group": "interactive_elements",
                        "name": f"element_{i+1}",
                        "text_value": element.text or "",
                        "id": selectors.get("id", ""),
                        "class": selectors.get("class", ""),
                        "css": selectors.get("css", ""),
                        "xpath": selectors.get("xpath", ""),
                        "full_xpath": selectors.get("full_xpath", ""),
                        "element_type": element_type,
                        "category": element.category
                    })
                
                # セレクタのサンプル表示
                print("\n--- CSVで使用できるセレクタのサンプル (最大10件) ---")
                for selector in converted_selectors[:10]:
                    print(f"{selector['group']},{selector['name']},{selector['text_value']},{selector['id']},{selector['class']},{selector['css']},{selector['xpath']},{selector['element_type']},{selector['category']}")
                
                # 結果をセレクタとして出力
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = os.path.join(args.output_dir, f"interactive_elements_{now_str}.csv")
                json_filename = os.path.join(args.output_dir, f"interactive_elements_{now_str}.json")
                
                # セレクタをCSVに出力
                with open(csv_filename, "w", encoding="utf-8", newline="") as csvfile:
                    fieldnames = ["group", "name", "text_value", "id", "class", "css", "xpath", "full_xpath", "element_type", "category"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for selector in converted_selectors:
                        writer.writerow(selector)
                        
                # セレクタをJSONに出力
                with open(json_filename, "w", encoding="utf-8") as jsonfile:
                    json.dump(converted_selectors, jsonfile, ensure_ascii=False, indent=2)
                    
                print(f"\nセレクタをCSVファイルに出力しました: {csv_filename}")
                print(f"セレクタをJSONファイルに出力しました: {json_filename}")
            else:
                logger.error("インタラクティブ要素が見つかりませんでした")
        
        # 通常のページ解析を実行
        if not search_performed or args.save_html:
            # ページ要素を分析
            result = analyzer.analyze_page(save_html=args.save_html)
            
            if not result["success"]:
                logger.error("ページ分析に失敗しました")
                return 1
                
            # HTMLソースが保存された場合
            if result["html_file"]:
                logger.info(f"HTMLソースが保存されました: {result['html_file']}")
                
            # 要素テーブルを表示（検索モードでは表示しない）
            if not search_performed:
                analyzer.print_element_tables()
                
                # カテゴリーサマリーを表示
                analyzer.print_category_summary()
            
            # セレクタを収集
            if not search_performed:
                selectors = analyzer.collect_selectors()
                
                # 現在のタイムスタンプを取得
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # CSV出力ファイル名の決定
                csv_filename = None
                if args.csv_output:
                    csv_filename = args.csv_output
                elif args.output:
                    csv_filename = args.output
                else:
                    # デフォルトのファイル名を生成
                    csv_filename = f"selectors_{now_str}.csv"
                
                # JSON出力ファイル名の決定
                json_filename = None
                if args.json_output:
                    json_filename = args.json_output
                else:
                    # CSVファイル名から拡張子を変更してJSONファイル名を生成（常にJSON出力を有効化）
                    base_name = os.path.splitext(csv_filename)[0]
                    json_filename = f"{base_name}.json"
                
                # ファイル名がパスを含まない場合は、出力ディレクトリと結合
                if csv_filename and not os.path.isabs(csv_filename):
                    # 重複パスの問題を回避するためにbasename取得
                    if not csv_filename.startswith(args.output_dir):
                        csv_filename = os.path.join(args.output_dir, os.path.basename(csv_filename))
                
                if json_filename and not os.path.isabs(json_filename):
                    # 重複パスの問題を回避するためにbasename取得
                    if not json_filename.startswith(args.output_dir):
                        json_filename = os.path.join(args.output_dir, os.path.basename(json_filename))
                
                # 出力ディレクトリが存在することを確認
                os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
                if json_filename:
                    os.makedirs(os.path.dirname(json_filename), exist_ok=True)
                
                # セレクタ情報をCSVとJSONに出力
                logger.info(f"セレクタを出力します - CSV: {csv_filename}, JSON: {json_filename}")
                
                # ファイル名を渡して出力
                if analyzer.export_selectors(selectors, csv_filename, json_filename):
                    logger.info("セレクタの出力が完了しました")
                    print(f"\nセレクタをCSVファイルに出力しました: {csv_filename}")
                    print(f"セレクタをJSONファイルに出力しました: {json_filename}")
                else:
                    logger.warning("セレクタの出力中に一部エラーが発生しました")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断が検出されました")
        return 1
        
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        return 1
        
    finally:
        # ブラウザを閉じる
        analyzer.close()


if __name__ == "__main__":
    sys.exit(main()) 