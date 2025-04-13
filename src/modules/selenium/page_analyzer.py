"""
ページ解析モジュール

Seleniumを利用してウェブページの解析を行うユーティリティクラスです。
"""

import logging
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class PageAnalyzer:
    """ウェブページの解析を行うクラス"""
    
    def __init__(self, browser, logger=None):
        """
        PageAnalyzerの初期化
        
        Args:
            browser: Browserインスタンス
            logger: ロガーインスタンス
        """
        self.browser = browser
        self.logger = logger or logging.getLogger(__name__)
        
    def analyze_page_content(self, element_filter=None):
        """
        ページ内容を解析する
        
        Args:
            element_filter: 解析対象の要素フィルタ（辞書形式）
                例: {'forms': True, 'inputs': False, 'links': True}
                
        Returns:
            dict: 解析結果
        """
        # デフォルトのフィルタはすべての要素を含む
        if element_filter is None:
            element_filter = {
                'forms': True, 
                'inputs': True, 
                'buttons': True, 
                'links': True,
                'headings': True
            }
        
        # ページタイトルを取得
        page_title = self.browser.driver.title
        
        # 結果を格納する辞書
        result = {
            'page_title': page_title,
            'page_url': self.browser.driver.current_url,
            'page_status': self._get_page_status(),
            'forms': [],
            'inputs': [],
            'buttons': [],
            'links': [],
            'headings': []
        }
        
        # 解析対象要素を収集
        if element_filter.get('forms', False):
            result['forms'] = self._find_forms()
            
        if element_filter.get('inputs', False):
            result['inputs'] = self._find_inputs()
            
        if element_filter.get('buttons', False):
            result['buttons'] = self._find_buttons()
            
        if element_filter.get('links', False):
            result['links'] = self._find_links()
            
        if element_filter.get('headings', False):
            result['headings'] = self._find_headings()
        
        return result
    
    def find_element_by_text(self, text, case_sensitive=True, partial_match=True, max_retries=3, retry_interval=1):
        """
        テキストで要素を検索する
        
        Args:
            text: 検索するテキスト
            case_sensitive: 大文字小文字を区別するか
            partial_match: 部分一致を許可するか
            max_retries: リトライ回数
            retry_interval: リトライ間隔（秒）
            
        Returns:
            list: 見つかった要素のリスト（辞書形式）
        """
        result = []
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # ページソースを取得
                page_source = self.browser.driver.page_source
                if not page_source:
                    raise Exception("ページソースが取得できません")
                    
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # テキストを含む要素をすべて取得
                for element in soup.find_all(text=lambda t: self._match_text(t, text, case_sensitive, partial_match)):
                    try:
                        parent = element.parent
                        if not parent:
                            continue
                            
                        xpath = self._generate_xpath(parent)
                        if not xpath:
                            continue
                        
                        # XPathで実際の要素を取得
                        try:
                            web_element = WebDriverWait(self.browser.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, xpath))
                            )
                            
                            # 要素の表示状態を確認
                            try:
                                is_displayed = web_element.is_displayed()
                            except:
                                is_displayed = False
                                
                            if is_displayed:
                                result.append({
                                    'element': web_element,
                                    'text': web_element.text,
                                    'tag': parent.name,
                                    'xpath': xpath,
                                    'is_displayed': is_displayed
                                })
                        except:
                            continue
                            
                    except Exception as e:
                        self.logger.debug(f"要素の処理中にエラーが発生しました: {str(e)}")
                        continue
                
                # 要素が見つかった場合は終了
                if result:
                    return result
                    
                # 要素が見つからない場合はリトライ
                retry_count += 1
                if retry_count < max_retries:
                    self.logger.warning(f"要素が見つかりません。リトライします ({retry_count}/{max_retries})")
                    time.sleep(retry_interval)
                    
                    # ページの再読み込みを試みる
                    try:
                        self.browser.driver.refresh()
                        WebDriverWait(self.browser.driver, 10).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                    except:
                        pass
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.error(f"テキストによる要素検索中にエラーが発生しました: {str(e)}")
                    break
                    
                self.logger.warning(f"エラーが発生しました。リトライします ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_interval)
        
        return result
    
    def find_interactive_elements(self):
        """
        インタラクティブな要素を検索する
        
        Returns:
            dict: クリック可能な要素と入力フィールドのリスト
        """
        result = {
            'clickable': [],
            'input': []
        }
        
        try:
            # クリック可能な要素（ボタン、リンク、チェックボックスなど）
            for selector in [
                'button', 'a', 'input[type="button"]', 'input[type="submit"]',
                'input[type="checkbox"]', 'input[type="radio"]', '.btn', '[role="button"]'
            ]:
                elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        result['clickable'].append({
                            'element': element,
                            'tag': element.tag_name,
                            'text': element.text or element.get_attribute('value') or '',
                            'location': element.location
                        })
            
            # 入力フィールド
            for selector in [
                'input[type="text"]', 'input[type="email"]', 'input[type="password"]',
                'input[type="search"]', 'input[type="tel"]', 'input[type="url"]',
                'input[type="number"]', 'input[type="date"]', 'textarea', 'select'
            ]:
                elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        result['input'].append({
                            'element': element,
                            'tag': element.tag_name,
                            'type': element.get_attribute('type') or '',
                            'name': element.get_attribute('name') or '',
                            'placeholder': element.get_attribute('placeholder') or ''
                        })
        
        except Exception as e:
            self.logger.error(f"インタラクティブ要素の検索中にエラーが発生しました: {str(e)}")
        
        return result
    
    def detect_page_changes(self, wait_seconds=5):
        """
        ページの変化を検出する
        
        Args:
            wait_seconds: 変化を待機する秒数
            
        Returns:
            bool: 変化があった場合はTrue
        """
        try:
            # 現在のページソースを取得
            original_source = self.browser.driver.page_source
            
            # 指定時間待機
            time.sleep(wait_seconds)
            
            # 新しいページソースを取得
            new_source = self.browser.driver.page_source
            
            # ソースに違いがあるか確認
            return original_source != new_source
            
        except Exception as e:
            self.logger.error(f"ページ変化の検出中にエラーが発生しました: {str(e)}")
            return False
    
    def _match_text(self, text, search_text, case_sensitive, partial_match):
        """テキスト検索の条件に合うかチェック"""
        if text is None:
            return False
            
        if not case_sensitive:
            text = text.lower()
            search_text = search_text.lower()
            
        if partial_match:
            return search_text in text
        else:
            return text == search_text
    
    def _generate_xpath(self, element):
        """BeautifulSoupの要素からXPathを生成"""
        components = []
        current = element
        
        while current and current.name:
            siblings = current.find_previous_siblings(current.name)
            if siblings:
                components.append(f"{current.name}[{len(siblings) + 1}]")
            else:
                components.append(current.name)
            current = current.parent
            
        components.reverse()
        return '//' + '/'.join(components)
    
    def _get_page_status(self):
        """ページの状態を取得"""
        try:
            ready_state = self.browser.driver.execute_script("return document.readyState")
            page_height = self.browser.driver.execute_script("return document.body.scrollHeight")
            
            return {
                'ready_state': ready_state,
                'page_height': page_height,
                'url': self.browser.driver.current_url,
                'title': self.browser.driver.title
            }
        except Exception as e:
            self.logger.error(f"ページ状態の取得中にエラーが発生しました: {str(e)}")
            return {'ready_state': 'unknown', 'error': str(e)}
    
    def _find_forms(self):
        """フォーム要素を検索"""
        forms = []
        try:
            for form in self.browser.driver.find_elements(By.TAG_NAME, "form"):
                forms.append({
                    'element': form,
                    'action': form.get_attribute('action') or '',
                    'method': form.get_attribute('method') or 'get',
                    'id': form.get_attribute('id') or '',
                    'class': form.get_attribute('class') or ''
                })
        except Exception as e:
            self.logger.error(f"フォーム要素の検索中にエラーが発生しました: {str(e)}")
        return forms
    
    def _find_inputs(self):
        """入力要素を検索"""
        inputs = []
        try:
            for input_elem in self.browser.driver.find_elements(By.TAG_NAME, "input"):
                inputs.append({
                    'element': input_elem,
                    'type': input_elem.get_attribute('type') or 'text',
                    'name': input_elem.get_attribute('name') or '',
                    'id': input_elem.get_attribute('id') or '',
                    'placeholder': input_elem.get_attribute('placeholder') or '',
                    'value': input_elem.get_attribute('value') or ''
                })
                
            # textareaも追加
            for textarea in self.browser.driver.find_elements(By.TAG_NAME, "textarea"):
                inputs.append({
                    'element': textarea,
                    'type': 'textarea',
                    'name': textarea.get_attribute('name') or '',
                    'id': textarea.get_attribute('id') or '',
                    'placeholder': textarea.get_attribute('placeholder') or '',
                    'value': textarea.get_attribute('value') or textarea.text or ''
                })
                
            # selectも追加
            for select in self.browser.driver.find_elements(By.TAG_NAME, "select"):
                inputs.append({
                    'element': select,
                    'type': 'select',
                    'name': select.get_attribute('name') or '',
                    'id': select.get_attribute('id') or '',
                    'options': len(select.find_elements(By.TAG_NAME, "option"))
                })
                
        except Exception as e:
            self.logger.error(f"入力要素の検索中にエラーが発生しました: {str(e)}")
        return inputs
    
    def _find_buttons(self):
        """ボタン要素を検索"""
        buttons = []
        try:
            # button要素
            for button in self.browser.driver.find_elements(By.TAG_NAME, "button"):
                buttons.append({
                    'element': button,
                    'type': button.get_attribute('type') or 'button',
                    'id': button.get_attribute('id') or '',
                    'class': button.get_attribute('class') or '',
                    'text': button.text or ''
                })
                
            # input type="button"やtype="submit"も検索
            for input_btn in self.browser.driver.find_elements(By.CSS_SELECTOR, "input[type='button'], input[type='submit']"):
                buttons.append({
                    'element': input_btn,
                    'type': input_btn.get_attribute('type') or '',
                    'id': input_btn.get_attribute('id') or '',
                    'class': input_btn.get_attribute('class') or '',
                    'value': input_btn.get_attribute('value') or '',
                    'text': input_btn.get_attribute('value') or ''
                })
                
            # aタグでもクラスにbtnが含まれるものはボタンとして扱う
            for a_btn in self.browser.driver.find_elements(By.CSS_SELECTOR, "a.btn, a[role='button']"):
                buttons.append({
                    'element': a_btn,
                    'type': 'link-button',
                    'id': a_btn.get_attribute('id') or '',
                    'class': a_btn.get_attribute('class') or '',
                    'href': a_btn.get_attribute('href') or '',
                    'text': a_btn.text or ''
                })
                
        except Exception as e:
            self.logger.error(f"ボタン要素の検索中にエラーが発生しました: {str(e)}")
        return buttons
    
    def _find_links(self):
        """リンク要素を検索"""
        links = []
        try:
            for link in self.browser.driver.find_elements(By.TAG_NAME, "a"):
                links.append({
                    'element': link,
                    'href': link.get_attribute('href') or '',
                    'text': link.text or '',
                    'title': link.get_attribute('title') or '',
                    'id': link.get_attribute('id') or '',
                    'class': link.get_attribute('class') or ''
                })
        except Exception as e:
            self.logger.error(f"リンク要素の検索中にエラーが発生しました: {str(e)}")
        return links
    
    def _find_headings(self):
        """見出し要素を検索"""
        headings = []
        try:
            for level in range(1, 7):
                for heading in self.browser.driver.find_elements(By.TAG_NAME, f"h{level}"):
                    headings.append({
                        'element': heading,
                        'level': level,
                        'text': heading.text or '',
                        'id': heading.get_attribute('id') or '',
                        'class': heading.get_attribute('class') or ''
                    })
        except Exception as e:
            self.logger.error(f"見出し要素の検索中にエラーが発生しました: {str(e)}")
        return headings 