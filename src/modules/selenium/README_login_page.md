# LoginPage クラス仕様書

## 概要
汎用的なログインページ操作を提供するクラス。POMパターン（Page Object Model）を採用し、様々なWebサイトのログイン処理に対応。

## 特徴
- セレクタをCSVファイルで一元管理
- 複数のログインフォーム形式に対応
- アカウントキー認証対応
- エラーハンドリングとリトライ機能
- スクリーンショット自動取得
- 詳細なログ出力

## 基本的な使用方法

### 1. 初期化
```python
from src.modules.selenium.login_page import LoginPage

# 基本的な初期化
login_page = LoginPage(selector_group='login')

# カスタム設定での初期化
config = {
    'browser': {'headless': 'true'},
    'login': {
        'url': 'https://example.com/login',
        'max_attempts': 3
    }
}
login_page = LoginPage(config=config)
```

### 2. ログイン処理
```python
# シンプルなログイン
success = login_page.login()

# URLを指定してログイン
success = login_page.login(url='https://example.com/login')

# 最大試行回数を指定してログイン
success = login_page.login(max_attempts=5)
```

### 3. コンテキストマネージャーとしての使用
```python
with LoginPage() as login_page:
    success = login_page.login()
    if success:
        # 追加の処理
```

## セレクタの設定

### config/selectors.csv の例
```csv
group,name,selector_type,selector_value,description
login,username,id,username,ユーザー名入力欄
login,password,id,password,パスワード入力欄
login,login_button,css,.loginbtn,ログインボタン
login,account_key,id,account_key,アカウントキー入力欄
popup,login_notice,xpath,//div[@class='notice'],ログイン後通知
```

## メソッド一覧

### 初期化・設定関連
1. **__init__(selector_group='login', browser=None, logger=None, config=None)**
   - クラスの初期化
   - 引数:
     - selector_group: セレクタのグループ名
     - browser: 既存のブラウザインスタンス
     - logger: ロガーインスタンス
     - config: 設定辞書
   - 処理: セレクタ、ブラウザ、ロガー、設定の初期化

2. **_setup_default_logger()**
   - デフォルトのロガーをセットアップ
   - 戻り値: logging.Logger
   - 処理: ログフォーマット、ハンドラ、レベルの設定

3. **_init_browser(browser=None)**
   - ブラウザインスタンスを初期化
   - 引数:
     - browser: 既存のブラウザインスタンス
   - 戻り値: bool（成功時True）
   - 処理: ブラウザの設定とセットアップ

4. **_load_config()**
   - 設定を読み込む
   - 処理: URL、タイムアウト、認証、フォームフィールドの設定読み込み

### 設定読み込み関連
1. **_load_url_config()**
   - URL関連設定を読み込む
   - 処理: ログインURL、成功URLの設定

2. **_load_timeout_config()**
   - タイムアウト関連設定を読み込む
   - 処理: 最大試行回数、リダイレクト待機時間、要素待機時間の設定

3. **_load_auth_config()**
   - 認証関連設定を読み込む
   - 処理: ベーシック認証設定、認証情報の読み込み

4. **_load_form_fields()**
   - フォームフィールド設定を読み込む
   - 処理: ユーザー名、パスワード、アカウントキーの設定

5. **_load_validation_elements()**
   - 成功/失敗判定要素の設定を読み込む
   - 処理: 成功要素、エラー要素のセレクタ設定

### ログイン処理関連
1. **login(url=None, max_attempts=None)**
   - メインのログイン処理を実行
   - 引数:
     - url: ログインページのURL
     - max_attempts: 最大試行回数
   - 戻り値: bool（成功時True）
   - 処理: ログインページ遷移、フォーム入力、送信、結果確認

2. **navigate_to_login_page(url=None)**
   - ログインページに移動
   - 引数:
     - url: ログインページのURL
   - 戻り値: bool（成功時True）
   - 処理: ページ遷移とロード待機

3. **fill_login_form()**
   - ログインフォームに情報を入力
   - 戻り値: bool（成功時True）
   - 処理: フォームフィールドの入力

4. **submit_login_form()**
   - ログインフォームを送信
   - 戻り値: bool（成功時True）
   - 処理: フォーム送信とリダイレクト待機

### 検証・待機関連
1. **wait_for_page_load(timeout=None)**
   - ページのロード完了を待機
   - 引数:
     - timeout: タイムアウト秒数
   - 戻り値: bool（成功時True）

2. **wait_for_element(locator, timeout=None, visible=True)**
   - 要素が表示されるまで待機
   - 引数:
     - locator: 要素のロケータ
     - timeout: タイムアウト秒数
     - visible: 可視性確認
   - 戻り値: WebElement or None

3. **wait_for_login_redirect()**
   - ログイン後のリダイレクトを待機
   - 戻り値: bool（成功時True）

4. **check_login_result()**
   - ログイン結果を確認
   - 戻り値: bool（成功時True）
   - 処理: 成功要素、エラー要素、URLの確認

### エラーハンドリング関連
1. **_notify_error(error_message, exception=None, context=None)**
   - エラーを通知
   - 引数:
     - error_message: エラーメッセージ
     - exception: 例外オブジェクト
     - context: コンテキスト情報

2. **_extract_login_error_message()**
   - ログインエラーメッセージを抽出
   - 戻り値: str or None
   - 処理: エラーメッセージの検索と抽出

### リダイレクト処理関連
1. **detect_and_handle_auth_redirect()**
   - 認証画面へのリダイレクトを検出して処理
   - 戻り値: bool（処理成功時True）
   - 処理: アカウントキー認証の処理

2. **_handle_post_login_notices()**
   - ログイン後のお知らせやポップアップを処理
   - 処理: 通知の検出と閉じる処理

### ユーティリティ関連
1. **_get_config_value(section, key, default)**
   - 設定値を取得
   - 引数:
     - section: 設定セクション
     - key: 設定キー
     - default: デフォルト値
   - 戻り値: Any（設定値）

2. **_embed_basic_auth_to_url(url, username, password)**
   - URLにベーシック認証情報を埋め込む
   - 引数:
     - url: 元のURL
     - username: ユーザー名
     - password: パスワード
   - 戻り値: str（認証情報付きURL）

### リソース管理関連
1. **close()**
   - ブラウザを閉じる
   - 処理: リソースの解放

2. **__enter__() / __exit__()**
   - コンテキストマネージャー対応
   - 処理: withブロックでのリソース管理

## エラーハンドリング

### LoginError 例外
```python
try:
    login_page.login()
except LoginError as e:
    print(f"ログインエラー: {str(e)}")
```

### エラーメッセージの取得
```python
error_message = login_page._extract_login_error_message()
if error_message:
    print(f"エラー: {error_message}")
```

## 設定ファイル

### settings.ini の例
```ini
[LOGIN]
url = https://example.com/login
success_url = https://example.com/dashboard
max_attempts = 3
redirect_timeout = 10
element_timeout = 5
page_load_wait = 1
screenshot_on_login = true
basic_auth_enabled = false
```

### secrets.env の例
```env
LOGIN_USERNAME=your_username
LOGIN_PASSWORD=your_password
LOGIN_ACCOUNT_KEY=your_account_key
```

## スクリーンショット機能

### スクリーンショット取得タイミング
1. ログインページ表示時
2. フォーム入力後
3. エラー発生時
4. ログイン成功時
5. ポップアップ表示時

### スクリーンショット設定
```ini
[BROWSER]
screenshot_dir = logs/screenshots
screenshot_format = png
screenshot_quality = 80
screenshot_on_error = true
```

## ログ出力

### ログレベル
- INFO: 通常の処理状況
- WARNING: 軽度の問題
- ERROR: 重大な問題
- DEBUG: 詳細なデバッグ情報

### ログ出力例
```
2024-04-09 10:00:00 - login_page - [INFO] - ログイン処理を開始します
2024-04-09 10:00:01 - login_page - [INFO] - ユーザー名入力欄を確認しました
2024-04-09 10:00:02 - login_page - [INFO] - ログインボタンをクリックしました
2024-04-09 10:00:03 - login_page - [INFO] - ログインに成功しました
```

## 拡張方法

### カスタムログイン処理の追加
```python
class CustomLoginPage(LoginPage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def custom_login_process(self):
        # カスタムログイン処理の実装
        pass
```

### セレクタの追加
1. selectors.csv にセレクタを追加
2. 必要に応じてメソッドをオーバーライド

## 注意事項
1. ブラウザインスタンスの管理
2. タイムアウト設定の調整
3. エラーハンドリングの実装
4. スクリーンショットの保存場所
5. ログ出力の管理

## トラブルシューティング

### よくある問題と解決方法
1. セレクタが見つからない
   - selectors.csv の内容を確認
   - ページの構造変更を確認

2. タイムアウトエラー
   - タイムアウト値の調整
   - ネットワーク状態の確認

3. 認証エラー
   - 認証情報の確認
   - 環境変数の設定確認

4. リダイレクトエラー
   - success_url の確認
   - redirect_timeout の調整 