# Webページセレクタ抽出ツール

このツールは、ウェブページから要素のセレクタ情報（ID、class、CSS、XPath、full XPath）を抽出するためのPythonスクリプトです。Seleniumを使用してウェブページの要素を解析し、自動化テストやウェブスクレイピングに使用できるセレクタ情報を収集します。

## 機能

- ウェブページの要素からID、class、CSS、XPath、full XPathを自動的に収集
- クリック可能な要素（リンク、ボタンなど）と入力フィールドを検出
- 要素情報をCSVとJSON形式で出力
- 要素情報の要約を表示

## 必要条件

- Python 3.6以上
- 以下のPythonパッケージ:
  - selenium
  - webdriver-manager

## インストール

1. 依存パッケージをインストールします:

```bash
pip install selenium webdriver-manager
```

## 使い方

### 基本的な使用方法

コマンドラインからスクリプトを実行します:

```bash
python extract_selectors.py https://example.com
```

### コマンドラインオプション

```
python extract_selectors.py [URL] [オプション]

引数:
  url                   解析するウェブページのURL

オプション:
  --output-dir OUTPUT_DIR  出力ディレクトリ (デフォルト: "data/page_analyze")
  --wait-time WAIT_TIME    ページロード待機時間（秒） (デフォルト: 5)
  --headless               ヘッドレスモードで実行 (ブラウザを表示せずに実行)
```

### 出力ファイル

スクリプトは以下のファイルを生成します:

1. `selectors_analysis_YYYYMMDD_HHMMSS.csv` - タイムスタンプ付きの詳細な要素情報
2. `selectors_analysis_YYYYMMDD_HHMMSS.json` - タイムスタンプ付きの詳細な要素情報（JSON形式）
3. `all_selectors.csv` - セレクタタイプごとの情報（ID、class、CSS、XPath、full XPath）
4. `all_selectors.json` - セレクタタイプごとの情報（JSON形式）

## 出力例

### `all_selectors.csv`

```
group,name,text_value,id,class,css,xpath,full_xpath,element_type
detailed_analysis,login_button,ログイン,login_btn,btn btn-primary,#login_btn,//button[text()='ログイン'],/html/body/div/div/form/button[1],クリック可能
detailed_analysis,username_input,,username,form-control,#username,//input[@id='username'],/html/body/div/div/form/div[1]/input,入力フィールド
...
```

## Seleniumでの使用例

生成されたセレクタ情報を使用してSeleniumでウェブ要素にアクセスする例:

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://example.com")

# IDを使用
element = driver.find_element(By.ID, "login_btn")

# クラスを使用
element = driver.find_element(By.CLASS_NAME, "btn-primary")

# CSSセレクタを使用
element = driver.find_element(By.CSS_SELECTOR, "#login_btn")

# XPathを使用
element = driver.find_element(By.XPATH, "//button[text()='ログイン']")

# フルXPathを使用
element = driver.find_element(By.XPATH, "/html/body/div/div/form/button[1]")
```

## 注意事項

- ウェブサイトによっては、ロボット検出や制限がある場合があります。利用規約を確認してください。
- 動的に生成される要素は、十分な待機時間を設定することで捕捉できる可能性が高まります。
- フルXPathは、ウェブサイトの構造が変更された場合に壊れやすい傾向があります。可能な限りID、クラス、または相対XPathを優先的に使用してください。
