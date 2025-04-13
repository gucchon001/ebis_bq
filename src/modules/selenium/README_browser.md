# Browser クラス仕様書

## 概要
Seleniumの機能をラップし、より使いやすく拡張した汎用的なブラウザ操作クラス。
設定ファイルを活用したスクリーンショット管理やセレクタ管理、エラーハンドリングを提供します。

## 特徴
- 設定ファイルによる柔軟な動作制御
- セレクタのCSVファイル管理
- 自動スクリーンショット機能
- 詳細なエラーハンドリング
- ページ解析機能
- 待機処理の最適化

## メソッド一覧

### 初期化・設定関連
1. **__init__(logger=None, selectors_path=None, headless=None, timeout=10, config=None, notifier=None, project_root=None)**
   - ブラウザインスタンスの初期化
   - 引数:
     - logger: カスタムロガー（指定されていない場合は新規作成）
     - selectors_path: セレクタを含むCSVファイルのパス
     - headless: ヘッドレスモードを有効にするかどうか
     - timeout: デフォルトのタイムアウト（秒）
     - config: 設定辞書（指定された場合はこれを優先使用）
     - notifier: 通知を送信するためのオブジェクト（省略可能）
     - project_root: プロジェクトのルートディレクトリ
   - 処理: ロガー、設定、セレクタ、ブラウザの初期化

2. **_get_project_root()**
   - プロジェクトのルートディレクトリを特定
   - 戻り値: str（プロジェクトルートのパス）
   - 処理: プロジェクトルートの検出とパス解決

3. **_resolve_path(path)**
   - 相対パスを絶対パスに解決
   - 引数:
     - path: 解決する相対パス
   - 戻り値: str（解決された絶対パス）

4. **_get_config_value(section, key, default)**
   - 設定値を取得
   - 引数:
     - section: 設定セクション
     - key: 設定キー
     - default: デフォルト値
   - 戻り値: Any（設定値）
   - 処理: 設定の優先順位に基づく値の取得

### セレクタ管理関連
1. **_load_selectors()**
   - CSVファイルからセレクタを読み込む
   - 処理: セレクタファイルの読み込みと解析

2. **_setup_fallback_selectors()**
   - フォールバックセレクタを設定
   - 処理: デフォルトセレクタの設定

3. **get_element(group, name, wait_time=None, visible=False)**
   - セレクタグループと名前を使用して要素を取得
   - 引数:
     - group: セレクタグループ
     - name: セレクタ名
     - wait_time: 待機時間（秒）
     - visible: 要素が表示されていることを確認するかどうか
   - 戻り値: WebElement or None

### ブラウザ操作関連
1. **setup(browser_version=None)**
   - ブラウザドライバーを初期化
   - 引数:
     - browser_version: 特定のブラウザバージョン（省略可）
   - 戻り値: bool（成功時True）
   - 処理: ドライバーの初期化と設定

2. **navigate_to(url)**
   - 指定URLに移動
   - 引数:
     - url: 移動先のURL
   - 戻り値: bool（成功時True）
   - 処理: ページ遷移とスクリーンショット取得

3. **wait_for_page_load(timeout=None)**
   - ページの読み込み完了を待機
   - 引数:
     - timeout: タイムアウト秒数
   - 戻り値: bool（成功時True）
   - 処理: ページ読み込み状態の確認

### 要素操作関連
1. **find_element(by, value, timeout=None)**
   - 要素を検索
   - 引数:
     - by: 検索方法（By.ID など）
     - value: セレクタ値
     - timeout: タイムアウト秒数
   - 戻り値: WebElement or None

2. **find_elements(by, value, timeout=None)**
   - 複数の要素を検索
   - 引数:
     - by: 検索方法
     - value: セレクタ値
     - timeout: タイムアウト秒数
   - 戻り値: List[WebElement]

3. **wait_for_element(by_or_tuple, value=None, condition=None, timeout=None, visible=False)**
   - 要素が特定の条件を満たすまで待機
   - 引数:
     - by_or_tuple: 検索方法またはタプル
     - value: セレクタ値
     - condition: 待機条件
     - timeout: タイムアウト秒数
     - visible: 可視性確認
   - 戻り値: WebElement or None

4. **click_element_by_selector(group, name, wait_time=None, use_js=False, retry_count=2)**
   - セレクタグループと名前を使用して要素を検索し、クリックする
   - 引数:
     - group: セレクタグループ
     - name: セレクタ名
     - wait_time: 要素を待機する時間（秒）
     - use_js: JavaScriptを使用したクリックを試みるかどうか
     - retry_count: クリック失敗時のリトライ回数
   - 戻り値: bool（成功時True）
   - 処理: 要素の検索、スクロール位置調整、通常/JS両方のクリック試行、エラー時の自動リトライ

### ページ解析関連
1. **analyze_page_content(element_filter=None, check_visibility=True)**
   - ページの内容を解析
   - 引数:
     - element_filter: フィルタリング設定
     - check_visibility: 可視要素のみ対象
   - 戻り値: dict（解析結果）
   - 処理: フォーム、ボタン、リンク、エラーメッセージなどの解析

2. **_get_page_status()**
   - ページのステータス情報を取得
   - 戻り値: dict（ステータス情報）
   - 処理: 読み込み状態、タイミング情報の取得

3. **get_page_title()**
   - 現在のページのタイトルを取得
   - 戻り値: str（ページタイトル）

4. **get_page_source()**
   - 現在のページのHTMLソースを取得
   - 戻り値: str（HTMLソース）

5. **get_current_url()**
   - 現在のURLを取得
   - 戻り値: str（現在のURL）

### スクリーンショット関連
1. **_load_screenshot_settings()**
   - スクリーンショット関連の設定を読み込む
   - 処理: スクリーンショット設定の初期化

2. **save_screenshot(filename, append_timestamp=False, append_url=False, custom_dir=None)**
   - スクリーンショットを保存
   - 引数:
     - filename: ファイル名
     - append_timestamp: タイムスタンプ付加
     - append_url: URL情報付加
     - custom_dir: 保存ディレクトリ
   - 戻り値: str（保存パス）

### ウィンドウ操作関連
1. **switch_to_new_window(current_handles=None, timeout=10, retries=3)**
   - 新しく開いたウィンドウに切り替え
   - 引数:
     - current_handles: 現在のウィンドウハンドル
     - timeout: タイムアウト秒数
     - retries: リトライ回数
   - 戻り値: bool（成功時True）

### 変更検出関連
1. **detect_page_changes(wait_seconds=3)**
   - ページの状態変化を検出
   - 引数:
     - wait_seconds: 待機秒数
   - 戻り値: bool（変化検出時True）
   - 処理: DOM変更、XHRリクエストの検出

### エラーハンドリング関連
1. **_notify_error(error_message, exception=None, context=None)**
   - エラーを通知
   - 引数:
     - error_message: エラーメッセージ
     - exception: 例外オブジェクト
     - context: コンテキスト情報
   - 処理: エラー通知とスクリーンショット取得

### リソース管理関連
1. **quit(error_message=None, exception=None, context=None)**
   - ブラウザを終了
   - 引数:
     - error_message: エラーメッセージ
     - exception: 例外オブジェクト
     - context: コンテキスト情報
   - 処理: リソースの解放とエラー通知

2. **close(error_message=None, exception=None, context=None)**
   - quit()のエイリアス
   - 処理: ブラウザの終了処理

## 基本的な使用方法

### 1. 初期化
```python
from src.modules.selenium.browser import Browser

# 基本的な初期化
browser = Browser()

# カスタム設定での初期化
config = {
    'BROWSER': {
        'headless': 'true',
        'timeout': 10,
        'screenshot_dir': 'logs/screenshots'
    }
}
browser = Browser(config=config)

# セットアップ
browser.setup()
```

### 2. 基本的な操作
```python
# ページ遷移
browser.navigate_to("https://example.com")

# 要素の検索
element = browser.find_element(By.ID, "username")

# 複数要素の検索
elements = browser.find_elements(By.CSS_SELECTOR, ".item")

# スクリーンショット取得
browser.save_screenshot("page_state")

# セレクタを使用した要素のクリック
browser.click_element_by_selector("login", "login_button")

# JavaScriptを使用した要素のクリック（要素が通常の方法でクリックできない場合）
browser.click_element_by_selector("menu", "hidden_button", use_js=True)
```

### 3. コンテキストマネージャーとしての使用
```python
with Browser() as browser:
    browser.setup()
    browser.navigate_to("https://example.com")
```

## セレクタ管理

### config/selectors.csv の構造
```csv
group,name,selector_type,selector_value,description
login,username,id,username,ユーザー名入力欄
login,password,id,password,パスワード入力欄
menu,home,css,.home-link,ホームリンク
```

### セレクタの使用
```python
# グループとセレクタ名で要素を取得
element = browser.get_element("login", "username")

# セレクタ情報の取得
selector_info = browser.selectors["login"]["username"]
```

## 設定ファイル

### settings.ini の例
```ini
[BROWSER]
headless = false
auto_screenshot = true
screenshot_dir = logs/screenshots
screenshot_format = png
screenshot_quality = 80
screenshot_on_error = true
window_width = 1366
window_height = 768
page_load_timeout = 10
timeout = 5
```

## エラーハンドリング

### エラー通知の設定
```python
from src.utils.notifier import Notifier

notifier = Notifier()
browser = Browser(notifier=notifier)
```

### エラー発生時の処理
```python
try:
    browser.navigate_to("https://example.com")
except Exception as e:
    browser._notify_error("ページ遷移エラー", e)
```

## ログ出力

### ログレベル
- DEBUG: 詳細な操作情報
- INFO: 通常の操作状況
- WARNING: 軽度の問題
- ERROR: 重大な問題

### ログ出力例
```
2024-04-09 11:00:00 - browser - [INFO] - ブラウザを初期化しました
2024-04-09 11:00:01 - browser - [INFO] - URLに移動します: https://example.com
2024-04-09 11:00:02 - browser - [INFO] - ページ読み込みが完了しました
```

## 拡張方法

### カスタムブラウザの作成
```python
class CustomBrowser(Browser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def custom_operation(self):
        # カスタム操作の実装
        pass
```

### メソッドのオーバーライド例
```python
def navigate_to(self, url):
    # 前処理
    result = super().navigate_to(url)
    # 後処理
    return result
```

## 注意事項
1. ブラウザドライバーの管理
2. メモリリークの防止
3. タイムアウト設定の最適化
4. スクリーンショットの保存容量
5. エラーハンドリングの実装

## トラブルシューティング

### よくある問題と解決方法
1. ドライバー初期化エラー
   - ChromeDriverのバージョン確認
   - Chromeブラウザの更新確認

2. 要素が見つからない
   - タイムアウト値の調整
   - セレクタの正確性確認
   - ページ読み込み待機の追加

3. スクリーンショットエラー
   - 保存ディレクトリの権限確認
   - ディスク容量の確認

4. メモリ使用量の増加
   - 定期的なブラウザの再起動
   - 不要なウィンドウ/タブの閉じる 