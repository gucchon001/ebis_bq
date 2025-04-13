# PageAnalyzer クラス仕様書

## 概要
Seleniumを利用してウェブページの解析を行うユーティリティクラスです。
ページ内の要素検索、状態分析、変更検知などの機能を提供します。

## 特徴
- 複数種類の要素の一括解析
- テキストベースの要素検索
- インタラクティブ要素の検出
- ページ状態の監視
- BeautifulSoupを活用したHTML解析

## メソッド一覧

### 初期化・設定関連
1. **__init__(browser, logger=None)**
   - PageAnalyzerの初期化
   - 引数:
     - browser: Browserインスタンス
     - logger: ロガーインスタンス（省略可）
   - 処理: ブラウザとロガーの初期化

### ページ解析関連
1. **analyze_page_content(element_filter=None)**
   - ページ内容を解析
   - 引数:
     - element_filter: 解析対象の要素フィルタ（辞書形式）
       例: {'forms': True, 'inputs': False, 'links': True}
   - 戻り値: dict（解析結果）
   - 処理: フォーム、入力、ボタン、リンク、見出しの解析

2. **_get_page_status()**
   - ページの状態を取得
   - 戻り値: dict
     - ready_state: ドキュメントの準備状態
     - page_height: ページの高さ
     - url: 現在のURL
     - title: ページタイトル

### 要素検索関連
1. **find_element_by_text(text, case_sensitive=True, partial_match=True)**
   - テキストで要素を検索
   - 引数:
     - text: 検索するテキスト
     - case_sensitive: 大文字小文字を区別するか
     - partial_match: 部分一致を許可するか
   - 戻り値: list（見つかった要素のリスト）

2. **find_interactive_elements()**
   - インタラクティブな要素を検索
   - 戻り値: dict
     - clickable: クリック可能な要素のリスト
     - input: 入力フィールドのリスト

### 要素収集関連
1. **_find_forms()**
   - フォーム要素を検索
   - 戻り値: list（フォーム要素のリスト）
   - 収集情報:
     - action: フォームの送信先
     - method: HTTPメソッド
     - id: 要素ID
     - class: CSSクラス

2. **_find_inputs()**
   - 入力要素を検索
   - 戻り値: list（入力要素のリスト）
   - 対象要素:
     - input要素
     - textarea要素
     - select要素

3. **_find_buttons()**
   - ボタン要素を検索
   - 戻り値: list（ボタン要素のリスト）
   - 対象要素:
     - button要素
     - input[type="button"]
     - input[type="submit"]
     - ボタンとして機能するaタグ

4. **_find_links()**
   - リンク要素を検索
   - 戻り値: list（リンク要素のリスト）
   - 収集情報:
     - href: リンク先URL
     - text: リンクテキスト
     - title: タイトル属性
     - id: 要素ID
     - class: CSSクラス

5. **_find_headings()**
   - 見出し要素を検索
   - 戻り値: list（見出し要素のリスト）
   - 収集情報:
     - level: 見出しレベル（h1-h6）
     - text: 見出しテキスト
     - id: 要素ID
     - class: CSSクラス

### 変更検知関連
1. **detect_page_changes(wait_seconds=5)**
   - ページの変化を検出
   - 引数:
     - wait_seconds: 変化を待機する秒数
   - 戻り値: bool（変化があった場合はTrue）
   - 処理: ページソースの比較による変更検知

### ユーティリティ関連
1. **_match_text(text, search_text, case_sensitive, partial_match)**
   - テキスト検索の条件に合うかチェック
   - 引数:
     - text: 対象テキスト
     - search_text: 検索テキスト
     - case_sensitive: 大文字小文字の区別
     - partial_match: 部分一致の許可
   - 戻り値: bool

2. **_generate_xpath(element)**
   - BeautifulSoupの要素からXPathを生成
   - 引数:
     - element: BeautifulSoup要素
   - 戻り値: str（XPath文字列）

## 基本的な使用方法

### 1. 初期化
```python
from src.modules.selenium.page_analyzer import PageAnalyzer
from src.modules.selenium.browser import Browser

# ブラウザの初期化
browser = Browser()
browser.setup()

# PageAnalyzerの初期化
analyzer = PageAnalyzer(browser)
```

### 2. ページ解析
```python
# 全要素の解析
result = analyzer.analyze_page_content()

# 特定の要素のみ解析
result = analyzer.analyze_page_content({
    'forms': True,
    'inputs': True,
    'buttons': False,
    'links': True,
    'headings': False
})
```

### 3. テキストによる要素検索
```python
# 完全一致検索
elements = analyzer.find_element_by_text("ログイン", case_sensitive=True, partial_match=False)

# 部分一致検索
elements = analyzer.find_element_by_text("ログイン", partial_match=True)
```

### 4. インタラクティブ要素の検索
```python
elements = analyzer.find_interactive_elements()
clickable = elements['clickable']  # クリック可能な要素
inputs = elements['input']  # 入力フィールド
```

## エラーハンドリング

### エラー発生時の処理
```python
try:
    result = analyzer.analyze_page_content()
except Exception as e:
    logger.error(f"ページ解析中にエラーが発生: {str(e)}")
```

## ログ出力

### ログレベル
- DEBUG: 詳細な解析情報
- INFO: 主要な解析結果
- WARNING: 軽度の問題
- ERROR: 解析エラー

### ログ出力例
```
2024-04-09 12:00:00 - page_analyzer - [INFO] - ページ解析を開始します
2024-04-09 12:00:01 - page_analyzer - [DEBUG] - フォーム要素を検出: 2件
2024-04-09 12:00:01 - page_analyzer - [INFO] - 解析完了
```

## 注意事項
1. メモリ使用量
   - 大量の要素を解析する場合はフィルタを使用
   - 必要な要素のみを収集

2. パフォーマンス
   - 不要な要素タイプは解析しない
   - 検索条件は具体的に指定

3. エラー処理
   - 要素が見つからない場合の処理
   - タイムアウトの考慮

4. DOM変更の検知
   - 動的なページでの使用
   - 変更検知のタイミング

## トラブルシューティング

### よくある問題と解決方法
1. 要素が見つからない
   - ページの読み込み完了を確認
   - 要素の可視性を確認
   - XPathの正確性を確認

2. パフォーマンスの問題
   - 解析対象を必要最小限に
   - キャッシュの活用
   - 待機時間の最適化

3. メモリ使用量の増加
   - 大きなページでの解析を分割
   - 不要な要素の解析を避ける 