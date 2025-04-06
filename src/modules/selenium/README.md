# 汎用ブラウザ自動化モジュール

このディレクトリには、ブラウザ自動化のための汎用的なクラスとユーティリティが含まれています。
プロジェクト固有の依存関係を持たず、様々なプロジェクトで再利用可能です。

## 主要なコンポーネント

### Browser クラス (`browser.py`)

`Browser` クラスは Selenium を使用したブラウザ自動化の基本機能を提供します。
主な特徴：

- プロジェクト固有の依存関係を排除し、環境変数や設定ファイルへの依存を抽象化（必要に応じてDIで注入）
- 一般的なメソッド名と引数で明確なインターフェースを提供
- オプション機能の柔軟な切り替え
- セレクタ管理、通知機能、ログ実装の独立したカスタマイズが可能
- 各メソッドでのエラーハンドリング、リトライ機能、スクリーンショット機能を実装

### LoginPage クラス (`login_page.py`)

`LoginPage` クラスは一般的なWebサイトのログイン処理を抽象化したクラスです。
`Browser` クラスと連携して動作し、POMパターン（Page Object Model）に基づいて実装されています。

主な特徴：

- セレクタをクラス変数として定義し、目的ごとにメソッドを分離（POMパターン）
- Browser クラスの汎用的なブラウザ操作機能を内部で使用
- 設定ファイルや環境変数からログイン情報を柔軟に読み込み
- ベーシック認証、多段階認証など様々な認証シナリオに対応
- エラーハンドリング、リトライ機能、スクリーンショット機能を実装
- with文でのリソース管理をサポート

## 使用方法

### 基本的な使用方法

```python
from modules.generic.browser import Browser

# ブラウザインスタンスの作成
browser = Browser(headless=False)

# ブラウザのセットアップ
if browser.setup():
    # Webサイトにアクセス
    browser.navigate_to("https://www.example.com")
    
    # 要素の操作
    element = browser.wait_for_element_by_id("username")
    if element:
        element.send_keys("testuser")
    
    # スクリーンショットの取得
    browser.save_screenshot("example.png")
    
    # ブラウザを閉じる
    browser.close()
```

### セレクタファイルを使用した例

```python
from modules.generic.browser import Browser

# セレクタファイルを指定してブラウザインスタンスを作成
browser = Browser(selectors_path="config/selectors.csv")

if browser.setup():
    browser.navigate_to("https://www.example.com")
    
    # セレクタファイルで定義された要素を使用
    browser.input_text("login", "username", "testuser")
    browser.input_text("login", "password", "password123")
    browser.click("login", "submit_button")
    
    # ブラウザを閉じる
    browser.close()
```

### LoginPageクラスを使用したログイン例

```python
from modules.generic.login_page import LoginPage

# 設定を定義
config = {
    'browser': {
        'headless': 'false'
    },
    'login': {
        'url': 'https://www.example.com/login',
        'username': 'testuser',
        'password': 'password123',
        'success_element_selector': '.welcome-message',
        'success_element_type': 'css'
    }
}

# withステートメントでLoginPageインスタンスを作成し、リソース管理を自動化
with LoginPage(config=config) as login_page:
    # ログイン処理の実行
    if login_page.login():
        print("ログインに成功しました")
        
        # ログイン後の処理
        # (ログイン後のページでの操作など)
    else:
        print("ログインに失敗しました")
```

## セレクタファイルの形式

セレクタファイルはCSV形式で、以下の構造を持ちます：

```
グループ,名前,セレクタ種別,セレクタ値,説明
login,username,id,username_field,ユーザー名入力欄
login,password,id,password_field,パスワード入力欄
login,login_button,css,button[type='submit'],ログインボタン
```

## 設計思想

このモジュールは以下の設計思想に基づいています：

1. **汎用性**: プロジェクト固有のコードを含まず、様々な場面で再利用可能
2. **拡張性**: 継承やコンポジションで機能を拡張しやすい設計
3. **安定性**: エラーハンドリングとリトライメカニズムによる安定した動作
4. **可読性**: 明確な命名規則と一貫したコードスタイル
5. **テスト容易性**: 依存関係を注入可能にし、単体テストが容易

## 依存関係

このモジュールは以下のライブラリに依存しています：

- Selenium
- webdriver_manager
- BeautifulSoup4（オプション、HTMLパース機能で使用）

## 制約事項

- このモジュールは Python 3.6 以上で動作します
- 特定のブラウザに依存する機能は、そのブラウザがインストールされている必要があります
- ヘッドレスモードで動作する場合、一部の機能（特にJavaScriptを多用するサイト）で制限がある場合があります 