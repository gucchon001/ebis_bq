"""
HTMLセレクタ解析ツール

ウェブページ内のクリック可能な要素や入力フィールドを検出し、
セレクタ情報をCSVおよびJSONファイルに出力します。

This module uses:
- Browser class from src.modules.selenium.browser
- PageAnalyzer class from src.modules.selenium.page_analyzer
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.modules.selenium.browser import Browser
from src.modules.selenium.page_analyzer import PageAnalyzer
from src.utils.environment import EnvironmentUtils

# ロガー設定
logger = logging.getLogger(__name__)

class HTMLSelectorAnalyzer:
    """
    HTMLページからセレクタ要素を抽出して保存するためのクラス
    
    このクラスは、指定されたURLのページを解析し、
    クリック可能な要素と入力フィールドを特定して
    標準化された形式でCSVとJSONファイルに出力します。
    """
    
    def __init__(self, 
                 output_dir: str = None, 
                 headless: bool = False,
                 logger: logging.Logger = None):
        """
        初期化
        
        Args:
            output_dir: 出力ディレクトリのパス（デフォルトは data/page_analyze）
            headless: ヘッドレスモードを使用するかどうか
            logger: カスタムロガー
        """
        # ロガー設定
        self.logger = logger or logging.getLogger(__name__)
        
        # 出力ディレクトリ設定
        self.output_dir = output_dir or os.path.join('data', 'page_analyze')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # ブラウザ設定
        self.headless = headless
        self.browser = None
        self.page_analyzer = None
        
        # 解析結果保存用
        self.selectors = []
        
    def setup(self) -> bool:
        """
        ブラウザをセットアップする
        
        Returns:
            bool: セットアップが成功したかどうか
        """
        try:
            # Browserインスタンスの作成
            self.browser = Browser(
                logger=self.logger,
                headless=self.headless
            )
            
            # ブラウザのセットアップ
            if not self.browser.setup():
                self.logger.error("ブラウザのセットアップに失敗しました")
                return False
                
            # PageAnalyzerインスタンスの作成
            self.page_analyzer = PageAnalyzer(self.browser, self.logger)
            
            self.logger.info("セレクタ解析ツールのセットアップが完了しました")
            return True
            
        except Exception as e:
            self.logger.error(f"セットアップ中にエラーが発生しました: {e}")
            return False
            
    def navigate_to(self, url: str) -> bool:
        """
        指定されたURLに移動する
        
        Args:
            url: アクセスするURL
            
        Returns:
            bool: 移動が成功したかどうか
        """
        if not self.browser:
            self.logger.error("ブラウザが初期化されていません")
            return False
            
        try:
            self.logger.info(f"ページに移動します: {url}")
            return self.browser.navigate_to(url)
        except Exception as e:
            self.logger.error(f"ページ移動中にエラーが発生しました: {e}")
            return False
            
    def analyze_page(self, save_html: bool = True) -> Dict[str, Any]:
        """
        ページ上の要素を解析する
        
        Args:
            save_html: HTMLソースを保存するかどうか
            
        Returns:
            Dict: 解析結果（成功フラグとHTMLファイルパス）
        """
        result = {
            "success": False,
            "html_file": None
        }
        
        if not self.browser or not self.page_analyzer:
            self.logger.error("ブラウザまたはページアナライザが初期化されていません")
            return result
            
        try:
            # HTMLソースの保存
            if save_html:
                html_source = self.browser.get_page_source()
                if html_source:
                    # HTMLファイル保存
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    html_filename = f"page_{now_str}.html"
                    html_path = os.path.join(self.output_dir, html_filename)
                    
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_source)
                        
                    self.logger.info(f"HTMLソースを保存しました: {html_path}")
                    result["html_file"] = html_path
                    
            # インタラクティブな要素を収集
            elements = self.page_analyzer.find_interactive_elements()
            
            # 結果を処理
            self._process_elements(elements)
            
            self.logger.info(f"ページ解析が完了しました（セレクタ: {len(self.selectors)}件）")
            result["success"] = True
            return result
            
        except Exception as e:
            self.logger.error(f"ページ解析中にエラーが発生しました: {e}")
            return result
            
    def _process_elements(self, elements: Dict[str, List[Dict[str, Any]]]):
        """
        収集された要素を処理してセレクタ情報に変換
        
        Args:
            elements: PageAnalyzerから取得した要素リスト
        """
        # セレクタのリストをクリア
        self.selectors = []
        
        # クリック可能な要素を処理
        for i, element in enumerate(elements.get('clickable', [])):
            try:
                # 要素の基本情報を取得
                element_obj = element.get('element')
                tag_name = element.get('tag', '')
                text = element.get('text', '')
                
                # 要素のID、クラス、属性を取得
                element_id = element_obj.get_attribute('id') or ''
                element_class = element_obj.get_attribute('class') or ''
                
                # データ属性を取得
                data_attributes = {}
                for attr in element_obj.get_property('attributes'):
                    attr_name = attr.get('name', '')
                    attr_value = attr.get('value', '')
                    if attr_name.startswith('data-') and attr_value:
                        data_attributes[attr_name] = attr_value
                
                # CSSセレクタの生成
                css_selector = self._generate_css_selector(element_obj)
                
                # XPathの生成
                xpath = self._generate_xpath(element_obj)
                
                # 完全なXPathの生成
                full_xpath = self._generate_full_xpath(element_obj)
                
                # カテゴリを特定
                category = self._determine_category(element_obj, tag_name, element_class)
                
                # セレクタ情報を作成
                selector_info = {
                    "group": "detailed_analysis",
                    "name": f"clickable_{i+1}",
                    "text_value": text,
                    "id": element_id,
                    "class": element_class,
                    "css": css_selector,
                    "xpath": xpath,
                    "full_xpath": full_xpath,
                    "element_type": "クリック可能",
                    "category": category
                }
                
                # データ属性を追加
                for key, value in data_attributes.items():
                    clean_key = key.replace("data-", "").replace("-", "_")
                    selector_info[clean_key] = value
                
                # 信頼性の高いセレクタを追加
                reliable_selectors = self._generate_reliable_selectors(
                    element_obj, tag_name, text, element_id, element_class, data_attributes
                )
                if reliable_selectors:
                    selector_info["reliable_selectors"] = reliable_selectors
                
                self.selectors.append(selector_info)
                
            except Exception as e:
                self.logger.debug(f"セレクタ情報作成中にエラーが発生しました (clickable_{i+1}): {e}")
        
        # 入力フィールドを処理
        for i, element in enumerate(elements.get('input', [])):
            try:
                # 要素の基本情報を取得
                element_obj = element.get('element')
                tag_name = element.get('tag', '')
                element_type = element.get('type', '')
                placeholder = element.get('placeholder', '')
                
                # テキスト値は、プレースホルダーまたは要素の値
                text_value = placeholder or element_obj.get_attribute('value') or ''
                
                # 要素のID、クラス、属性を取得
                element_id = element_obj.get_attribute('id') or ''
                element_class = element_obj.get_attribute('class') or ''
                
                # CSSセレクタの生成
                css_selector = self._generate_css_selector(element_obj)
                
                # XPathの生成
                xpath = self._generate_xpath(element_obj)
                
                # 完全なXPathの生成
                full_xpath = self._generate_full_xpath(element_obj)
                
                # セレクタ情報を作成
                selector_info = {
                    "group": "detailed_analysis",
                    "name": f"input_{i+1}",
                    "text_value": text_value,
                    "id": element_id,
                    "class": element_class,
                    "css": css_selector,
                    "xpath": xpath,
                    "full_xpath": full_xpath,
                    "element_type": "入力フィールド",
                    "category": "フォーム"
                }
                
                self.selectors.append(selector_info)
                
            except Exception as e:
                self.logger.debug(f"セレクタ情報作成中にエラーが発生しました (input_{i+1}): {e}")
    
    def _generate_css_selector(self, element) -> str:
        """
        要素のCSSセレクタを生成する
        
        Args:
            element: WebElement
            
        Returns:
            str: CSSセレクタ
        """
        try:
            # JavaScriptを使用してCSSセレクタを生成
            script = """
            function getCssSelector(el) {
                if (!el) return null;
                if (el.id) return `#${el.id}`;
                
                // クラス属性を使ったセレクタを試みる
                if (el.className && typeof el.className === 'string') {
                    const classes = el.className.trim().split(/\\s+/).filter(Boolean);
                    if (classes.length > 0) {
                        const classSelector = `.${classes.join('.')}`;
                        // このセレクタで一意に特定できるか確認
                        if (document.querySelectorAll(classSelector).length === 1) {
                            return classSelector;
                        }
                    }
                }
                
                // 親要素を含むパスを生成
                let path = [];
                let parent = el;
                while (parent && parent.nodeType === Node.ELEMENT_NODE) {
                    let selector = parent.nodeName.toLowerCase();
                    if (parent.id) {
                        selector = `#${parent.id}`;
                        path.unshift(selector);
                        break;
                    } else {
                        let sib = parent.previousElementSibling;
                        let nth = 1;
                        while (sib) {
                            if (sib.nodeName.toLowerCase() === selector) nth++;
                            sib = sib.previousElementSibling;
                        }
                        selector = nth > 1 ? `${selector}:nth-child(${nth})` : selector;
                    }
                    path.unshift(selector);
                    parent = parent.parentNode;
                    
                    // パスが長すぎる場合は途中で切り上げる
                    if (path.length > 3) break;
                }
                return path.join(' > ');
            }
            return getCssSelector(arguments[0]);
            """
            
            css_selector = self.browser.driver.execute_script(script, element)
            return css_selector or ""
            
        except Exception as e:
            self.logger.debug(f"CSSセレクタ生成中にエラーが発生しました: {e}")
            return ""
    
    def _generate_xpath(self, element) -> str:
        """
        要素のXPathを生成する
        
        Args:
            element: WebElement
            
        Returns:
            str: XPath
        """
        try:
            # ID属性があればIDベースのXPathを返す
            element_id = element.get_attribute('id')
            if element_id:
                return f"//*[@id='{element_id}']"
            
            # JavaScriptを使用してXPathを生成
            script = """
            function getXPath(element) {
                if (element && element.id) return `//*[@id="${element.id}"]`;
                
                const paths = [];
                for (; element && element.nodeType === Node.ELEMENT_NODE; element = element.parentNode) {
                    let index = 0;
                    for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                        if (sibling.nodeType === Node.DOCUMENT_TYPE_NODE) continue;
                        if (sibling.nodeName === element.nodeName) ++index;
                    }
                    const tagName = element.nodeName.toLowerCase();
                    const pathIndex = (index ? `[${index + 1}]` : '');
                    paths.unshift(tagName + pathIndex);
                }
                return '/' + paths.join('/');
            }
            return getXPath(arguments[0]);
            """
            
            xpath = self.browser.driver.execute_script(script, element)
            return xpath or ""
            
        except Exception as e:
            self.logger.debug(f"XPath生成中にエラーが発生しました: {e}")
            return ""
    
    def _generate_full_xpath(self, element) -> str:
        """
        要素の完全なXPathを生成する
        
        Args:
            element: WebElement
            
        Returns:
            str: 完全なXPath
        """
        try:
            # JavaScriptを使用して完全なXPathを生成
            script = """
            function getFullXPath(element) {
                const paths = [];
                for (; element && element.nodeType === Node.ELEMENT_NODE; element = element.parentNode) {
                    let index = 0;
                    for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                        if (sibling.nodeType === Node.DOCUMENT_TYPE_NODE) continue;
                        if (sibling.nodeName === element.nodeName) ++index;
                    }
                    const tagName = element.nodeName.toLowerCase();
                    const pathIndex = (index ? `[${index + 1}]` : '');
                    paths.unshift(tagName + pathIndex);
                }
                return '//*/' + paths.join('/');
            }
            return getFullXPath(arguments[0]);
            """
            
            full_xpath = self.browser.driver.execute_script(script, element)
            return full_xpath or ""
            
        except Exception as e:
            self.logger.debug(f"完全XPath生成中にエラーが発生しました: {e}")
            return ""
    
    def _determine_category(self, element, tag_name, element_class) -> str:
        """
        要素のカテゴリを特定する
        
        Args:
            element: WebElement
            tag_name: タグ名
            element_class: クラス名
            
        Returns:
            str: カテゴリ名
        """
        try:
            class_lower = element_class.lower()
            
            # カテゴリの判定ロジック
            if 'navbar' in class_lower or 'nav-' in class_lower or tag_name == 'nav':
                return 'ナビゲーションバー'
            elif 'sidebar' in class_lower or 'side-' in class_lower:
                return 'サイドバー'
            elif 'btn' in class_lower or tag_name == 'button':
                return 'ボタン'
            elif tag_name == 'a':
                return 'リンク'
            elif 'tab' in class_lower:
                return 'タブ'
            elif 'menu' in class_lower:
                return 'メニュー'
            elif 'header' in class_lower:
                return 'ヘッダー'
            elif 'footer' in class_lower:
                return 'フッター'
            
            # 位置情報からカテゴリを推定
            location = element.location
            if location['y'] < 100:
                return 'トップバー'
            elif location['x'] < 200:
                return 'サイドバー'
                
            # デフォルトカテゴリ
            return 'その他'
            
        except Exception as e:
            self.logger.debug(f"カテゴリ特定中にエラーが発生しました: {e}")
            return 'その他'
    
    def _generate_reliable_selectors(self, element, tag_name, text, element_id, element_class, data_attributes) -> List[Dict[str, str]]:
        """
        信頼性の高いセレクタを生成する
        
        Args:
            element: WebElement
            tag_name: タグ名
            text: テキスト値
            element_id: ID属性
            element_class: クラス属性
            data_attributes: データ属性
            
        Returns:
            List[Dict[str, str]]: 信頼性の高いセレクタのリスト
        """
        reliable_selectors = []
        
        # データ属性に基づくセレクタ（最も信頼性が高い）
        for attr_name, attr_value in data_attributes.items():
            if attr_value:
                css_selector = f"{tag_name}[{attr_name}='{attr_value}']"
                reliable_selectors.append({
                    "type": "css",
                    "value": css_selector
                })
        
        # ID属性に基づくセレクタ
        if element_id:
            reliable_selectors.append({
                "type": "css",
                "value": f"#{element_id}"
            })
        
        # クラス属性に基づくセレクタ
        if element_class and len(element_class.split()) < 3:  # 短いクラス名のみ
            reliable_selectors.append({
                "type": "css",
                "value": f".{element_class.replace(' ', '.')}"
            })
        
        # テキストに基づくXPathセレクタ
        if text and len(text) < 50:  # 短いテキストのみ
            safe_text = text.replace("'", "\\'")
            reliable_selectors.append({
                "type": "xpath",
                "value": f"//{tag_name}[text()='{safe_text}']"
            })
        
        return reliable_selectors
    
    def export_to_csv(self, filename: str = None) -> str:
        """
        セレクタ情報をCSVファイルにエクスポートする
        
        Args:
            filename: 出力ファイル名（Noneの場合は自動生成）
            
        Returns:
            str: 出力ファイルのパス（失敗時はNone）
        """
        if not self.selectors:
            self.logger.warning("エクスポートするセレクタ情報がありません")
            return None
        
        try:
            # ファイル名の設定
            if filename is None:
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"selectors_analysis_{now_str}.csv"
            
            # ファイルパスの設定
            file_path = os.path.join(self.output_dir, filename)
            
            # CSVファイルに出力
            with open(file_path, 'w', encoding='utf-8', newline='') as csvfile:
                # CSVに出力するフィールドを定義
                fieldnames = [
                    "group", "name", "text_value", "id", "class", 
                    "css", "xpath", "full_xpath", "element_type", "category"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for selector in self.selectors:
                    # 出力するフィールドだけを抽出
                    csv_row = {field: selector.get(field, "") for field in fieldnames}
                    writer.writerow(csv_row)
            
            self.logger.info(f"CSVファイルに {len(self.selectors)} 件のセレクタ情報を出力しました: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"CSV出力中にエラーが発生しました: {e}")
            return None
    
    def export_to_json(self, filename: str = None) -> str:
        """
        セレクタ情報をJSONファイルにエクスポートする
        
        Args:
            filename: 出力ファイル名（Noneの場合は自動生成）
            
        Returns:
            str: 出力ファイルのパス（失敗時はNone）
        """
        if not self.selectors:
            self.logger.warning("エクスポートするセレクタ情報がありません")
            return None
        
        try:
            # ファイル名の設定
            if filename is None:
                now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"selectors_analysis_{now_str}.json"
            
            # ファイルパスの設定
            file_path = os.path.join(self.output_dir, filename)
            
            # JSONファイルに出力
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.selectors, jsonfile, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSONファイルに {len(self.selectors)} 件のセレクタ情報を出力しました: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"JSON出力中にエラーが発生しました: {e}")
            return None
    
    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            self.browser.quit()
            self.logger.info("ブラウザを終了しました")

def main():
    """メイン関数"""
    import argparse
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='HTMLページからセレクタ要素を抽出するツール')
    parser.add_argument('url', help='解析するURL')
    parser.add_argument('--output-dir', '-o', help='出力ディレクトリ', default=None)
    parser.add_argument('--headless', '-hl', action='store_true', help='ヘッドレスモードを使用する')
    parser.add_argument('--csv', '-c', help='CSVファイル名', default='selectors_analysis.csv')
    parser.add_argument('--json', '-j', help='JSONファイル名', default='selectors_analysis.json')
    args = parser.parse_args()
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # セレクタ解析ツールの初期化
    analyzer = HTMLSelectorAnalyzer(
        output_dir=args.output_dir,
        headless=args.headless
    )
    
    try:
        # ブラウザのセットアップ
        if not analyzer.setup():
            return 1
        
        # URLに移動
        if not analyzer.navigate_to(args.url):
            return 1
        
        # ページ解析
        result = analyzer.analyze_page()
        if not result["success"]:
            return 1
        
        # CSVファイルに出力
        csv_path = analyzer.export_to_csv(args.csv)
        
        # JSONファイルに出力
        json_path = analyzer.export_to_json(args.json)
        
        if csv_path and json_path:
            print(f"解析結果をCSVファイルに保存しました: {csv_path}")
            print(f"解析結果をJSONファイルに保存しました: {json_path}")
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error(f"実行中にエラーが発生しました: {e}")
        return 1
        
    finally:
        # ブラウザを閉じる
        analyzer.close()

if __name__ == "__main__":
    import sys
    sys.exit(main()) 