# アドエビス CSVダウンロード機能 仕様書

## 1. 概要

本仕様書は、アドエビスの詳細分析ページからCSVファイルをダウンロードする機能の実装に関する仕様を定義します。
Seleniumを使用してブラウザ操作を自動化し、設定ファイルに基づいて動作します。

## 2. 設計原則

### 2.1. シンプル優先原則

- **直接性の原則**: 複雑な抽象化層は避け、Seleniumの基本APIを直接使用する
- **最小機能の原則**: 必要最小限の機能のみを実装し、過度な汎用性は追求しない
- **明確なエラーハンドリング**: エラー処理は最小限にしつつ、具体的で解決可能なメッセージを提供する

### 2.2. 実装方針

- 複雑なクラス階層は避け、機能単位で単一の関数またはクラスとして実装する
- ラッパークラスへの依存を最小化し、直接Seleniumのメソッドを呼び出す
- 環境変数から設定値を取得し、明示的にパラメータとして渡す

## 3. ログイン処理

### 3.1. 機能概要

アドエビスのログインページにアクセスし、環境変数から取得した認証情報を用いてログインを実行します。

### 3.2. 前提条件

- `config/secrets.env` ファイルに、アドエビスへのログインに必要な以下の情報が正しく設定されていること：
  - `EBIS_ACCOUNT_KEY`: アカウントキー
  - `EBIS_USERNAME`: ユーザー名
  - `EBIS_PASSWORD`: パスワード
- `config/settings.ini` ファイルの `[LOGIN]` セクションに、ログインページのURL (`url`) が正しく設定されていること
- 必要なSelenium WebDriver（例: ChromeDriver）が利用可能な状態であること (`webdriver_manager` を使用して自動管理)
- Python 仮想環境 (venv) が作成され、必要なパッケージがインストールされていること

### 3.3. ログイン処理の構成要素

#### 3.3.1. 関数ベースの実装

ログイン機能は単一の関数として実装します。この関数は以下のパラメータを受け取ります：
- ブラウザインスタンス（Seleniumのdriverを持つオブジェクト）
- アカウントキー（オプション、デフォルトでは環境変数から取得）
- ユーザー名（オプション、デフォルトでは環境変数から取得）
- パスワード（オプション、デフォルトでは環境変数から取得）

#### 3.3.2. 処理フロー

1. **環境変数から認証情報を取得**:
   - 引数で指定されていない場合、環境変数から各認証情報を取得
   - 認証情報が不足している場合はエラーとして処理

2. **ログインページに移動**:
   - 設定ファイルからログインURLを取得して移動
   - ページが適切に読み込まれるまで短時間待機

3. **要素検索と入力**:
   - 第8章の要素識別情報を参照して、アカウントキー入力フィールドに値を入力
   - 同様に、ユーザー名入力フィールドに値を入力
   - 同様に、パスワード入力フィールドに値を入力
   - 各要素が見つからない場合は適切なエラーログを記録

4. **ログインボタンクリック**:
   - 第8章の要素識別情報を参照して、ログインボタンをクリック
   - ページ遷移のために数秒間待機
   - ボタンが見つからない場合は適切なエラーログを記録

5. **ログイン後のポップアップ処理**:
   - ログイン成功後に表示される可能性のあるお知らせやポップアップを検出
   - 複数の検出パターン（クラス名、XPath）を使用して柔軟に対応
   - 閉じるボタンを探してクリック、またはESCキーで閉じるなど複数の対応方法を試行

#### 3.3.3. エラー処理

- **設定値不足**: `secrets.env` または `settings.ini` に必要なキーが存在しない場合にエラーメッセージを記録
- **ページ要素の欠損**: ログインページに必要な入力欄やボタンが見つからない場合にエラーログを記録し、スクリーンショットを保存
- **認証失敗**: 入力された認証情報が誤っている場合、ログインに失敗した旨をログに記録し、スクリーンショットを保存
- **タイムアウト**: ページ読み込みや要素の表示が指定時間内に完了しない場合、タイムアウトエラーをログに記録し、スクリーンショットを保存

### 3.4. 互換性のためのクラスインターフェース（オプション）

既存コードとの互換性が必要な場合は、シンプルなクラスで関数を包むインターフェースを提供します：

- 初期化時に最小限の設定のみを行う
- ログイン関数は内部で関数版の実装を呼び出す
- コンテキストマネージャのサポート（`__enter__`、`__exit__`）を提供する

## 4. CSVダウンロード処理

### 4.1. 機能概要

アドエビスの詳細分析ページとコンバージョン属性ページにアクセスし、指定した条件（レポートタイプ、日付範囲など）でCSVファイルをダウンロードします。

### 4.2. 前提条件

- ログイン機能が正常に動作する状態であること
- `config/settings.ini` ファイルの `[CSV_DOWNLOAD]` セクションに、必要な設定が正しく定義されていること
  - `analysis_url`: 詳細分析ページのURL
  - `cv_attribute_url`: コンバージョン属性ページのURL
- 実行環境がCSVダウンロードに必要な権限を持っていること（ファイル書き込み権限など）
- Chromeブラウザでダウンロード設定（自動ダウンロードと保存先の指定）が可能であること
- Python 仮想環境 (venv) が有効化されていること

### 4.3. 設定ファイル

- **`config/settings.ini`**:
  - `[CSV_DOWNLOAD]` セクション
    - `download_dir`: ダウンロードしたCSVファイルの保存先ディレクトリ。デフォルトは `data/downloads`
    - `analysis_url`: 詳細分析ページのURL（オプション。指定がない場合はメニューから遷移）
    - `element_timeout`: 要素の表示待機時間（秒）。デフォルトは5秒
    - `download_timeout`: ダウンロード完了の待機時間（秒）。デフォルトは60秒
    - `page_load_wait`: ページ読み込み後の追加待機時間（秒）。デフォルトは1秒
  - `[BROWSER]` セクション
    - `headless`: ヘッドレスモードで実行するかどうか（"true"/"false"）

### 4.4. 実装方法

#### 4.4.1. 関数ベースの実装

CSVダウンロード機能は以下の関数として実装します：

1. **詳細分析レポートのダウンロード関数**:
   - ブラウザインスタンス
   - CSVタイプ（"detailed_analysis"など）
   - 開始日（YYYY-MM-DD形式）
   - 終了日（YYYY-MM-DD形式）
   - ダウンロード先ディレクトリ
   - トラフィックタイプ（オプション、デフォルトは"all"）：表示するデータの種類を指定（"all", "organic", "direct", "referral", "social", "paid"など）

2. **コンバージョン属性レポートのダウンロード関数**:
   - ブラウザインスタンス
   - 開始日（YYYY-MM-DD形式）
   - 終了日（YYYY-MM-DD形式）
   - ダウンロード先ディレクトリ
   - トラフィックタイプ（オプション、デフォルトは"all"）：表示するデータの種類を指定（"all", "organic", "direct", "referral", "social", "paid"など）

#### 4.4.2. 処理フロー

**詳細分析レポートのダウンロード処理**:

1. **詳細分析ページに移動**:
   - 設定ファイルから詳細分析ページのURLを取得して移動
   - ページが適切に読み込まれるまで待機
   - URLが設定されていない場合は、ダッシュボードからメニューを辿って詳細分析ページにアクセス

2. **日付範囲設定**:
   - 第8章の要素識別情報を参照して、日付ピッカーボタンをクリック
   - 開始日入力フィールドを見つけて値をクリアし、指定された日付を入力
   - 終了日入力フィールドを見つけて値をクリアし、指定された日付を入力
   - 適用ボタンをクリック
   - 開始日と終了日が指定されていない場合、デフォルト値（終了日 = 今日、開始日 = 30日前）を使用

3. **トラフィックタブの選択**:
   - 日付範囲設定の後、必ず全トラフィックタブを選択する
   - 全トラフィックタブは、設定が変更されるたびに毎回明示的に選択する必要がある
   - traffic_typeが"all"の場合でも、必ず全トラフィックタブをクリックする
   - タブ選択後、ページ内容が更新されるまで短時間待機する

4. **CSVダウンロード**:
   - 第8章の要素識別情報を参照して、ダウンロードボタンをクリック
   - ユーザーのデフォルトダウンロードフォルダ（`C:\Users\ユーザー名\Downloads`）内の既存CSVファイル一覧を取得
   - ダウンロード完了を待機（専用の待機関数を使用）
   - ダウンロードされたファイルの完全パスを取得

5. **ダウンロードファイルの検出と処理**:
   - ブラウザはデフォルトで `C:\Users\ユーザー名\Downloads` フォルダにファイルをダウンロードする
   - ユーザーのデフォルトダウンロードフォルダのみを監視し、ダウンロード前に取得したファイル一覧と比較して新しいCSVファイルを検出
   - 新しく追加されたCSVファイルを特定し、最新のファイルを取得
   - ファイルがロックされていないこと（完全にダウンロードが完了していること）を確認
   - 指定されたタイムアウト時間内にファイルが検出されない場合は、Browser.get_latest_download()メソッドを使って最終的なチェックを行う
   - 検出されたCSVファイルをプログラム指定のディレクトリ（デフォルト: `data/downloads`）に移動
   - 日付とレポートタイプに基づいたファイル名に統一（例: `YYYYMMDD_ebis_detailed_report.csv`）
   - 移動先のファイルがすでに存在する場合は、バックアップを作成
   - CSVファイルにA列として「日付」列を追加する処理を実行
     - ヘッダ行には「日付」という名称を追加
     - データ行には前日の日付（YYYY-MM-DD形式）を追加
     - 文字コードを適切に検出して処理を行い、元のファイルを上書き
   - ファイルのリネーム・移動・加工後の完全パスを返却

**コンバージョン属性レポートのダウンロード処理**:

1. **コンバージョン属性ページに移動**:
   - 設定ファイルからコンバージョン属性ページのURLを取得して移動
   - ページが適切に読み込まれるまで待機
   - URLが設定されていない場合はエラーとして処理

2. **日付範囲設定**:
   - 開始日と終了日が指定されている場合のみ設定を行う
   - 指定されていない場合はデフォルト値を使用（設定不要）

3. **トラフィックタブの選択**:
   - 全トラフィックタブを選択
   - タブ選択後、ページ内容が更新されるまで短時間待機

4. **CSVダウンロード**:
   - ユーザーのデフォルトダウンロードフォルダ内の既存CSVファイル一覧を取得
   - CSVボタンをクリック
   - 表を出力（CSV）ボタンをクリック
   - ダウンロード完了を待機（専用の待機関数を使用）
   - ダウンロードされたファイルの完全パスを取得

5. **ダウンロードファイルの検出と処理**:
   - ブラウザはデフォルトで `C:\Users\ユーザー名\Downloads` フォルダにファイルをダウンロードする
   - ユーザーのデフォルトダウンロードフォルダのみを監視し、ダウンロード前に取得したファイル一覧と比較して新しいCSVファイルを検出
   - 新しく追加されたCSVファイルを特定し、最新のファイルを取得
   - ファイルがロックされていないこと（完全にダウンロードが完了していること）を確認
   - 指定されたタイムアウト時間内にファイルが検出されない場合は、Browser.get_latest_download()メソッドを使って最終的なチェックを行う
   - 検出されたCSVファイルをプログラム指定のディレクトリ（デフォルト: `data/downloads`）に移動
   - コンバージョン属性レポート用のファイル名に統一（例: `YYYYMMDD_ebis_CVrepo.csv`）
   - 移動先のファイルがすでに存在する場合は、バックアップを作成
   - CSVファイルにA列として「日付」列を追加する処理を実行
   - ファイルのリネーム・移動・加工後の完全パスを返却

#### 4.4.3. ダウンロード待機処理

ダウンロード完了を待機する専用の処理を実装します：
- ユーザーのデフォルトダウンロードフォルダ（`C:\Users\ユーザー名\Downloads`）のみを監視
- ダウンロード前後のCSVファイル一覧を比較し、新しく追加されたファイルを特定
- ポーリング間隔を調整（初期は短い間隔で、時間経過とともに長くする）で効率的に監視
- ファイルサイズが0より大きいこと、およびファイルがロックされていないこと（完全にダウンロード完了）を確認
- 指定されたタイムアウト時間（`download_timeout`）を超えた場合はエラーとして処理

#### 4.4.4. ファイル命名規則と保存形式

ダウンロードされたCSVファイルは、以下の命名規則に従って保存されます：

1. **ファイル命名規則**:
   - 詳細分析レポート: `YYYYMMDD_ebis_detailed_report.csv`
   - コンバージョン属性レポート: `YYYYMMDD_ebis_CVrepo.csv`
   - その他のレポートタイプ: `YYYYMMDD_ebis_{report_type}_report.csv`
   - YYYYMMDD部分は処理実行日（または指定された日付）

2. **保存フローと代替処理**:
   - ブラウザはユーザーのデフォルトダウンロードフォルダ（`C:\Users\ユーザー名\Downloads`）にファイルを保存
   - プログラムはダウンロードを検知後、CSVファイルを設定された `download_dir` または指定されたディレクトリに移動
   - 同名ファイルが既に存在する場合は `.bak` 拡張子でバックアップを作成
   - ファイル移動に失敗した場合は、コピー処理を試行
   - すべての処理が失敗した場合は、元のダウンロードパスを返却

3. **ファイル内容の加工処理**:
   - CSVファイルにA列として「日付」列を追加
   - ヘッダ行には「日付」という列名を設定
   - データ行にはすべて前日の日付（YYYY-MM-DD形式）を入力
   - ファイルの文字コードを自動検出し、適切なエンコーディングで処理
   - 加工処理はファイルの移動または複製の後に実行

### 4.5. エラー処理

- **ブラウザ初期化エラー**: ブラウザのセットアップに失敗した場合に発生するエラーを記録
- **ページ遷移エラー**: 詳細分析ページへのアクセスに失敗した場合に発生するエラーを記録
- **要素検出エラー**: 必要な要素（日付ボタン、CSVダウンロードボタンなど）が見つからない場合に発生するエラーを記録
- **ダウンロード検証エラー**: 指定時間内にCSVファイルのダウンロードが完了しなかった場合に発生するエラーを記録

## 5. テスト実行プロセス

以下の順序でテスト実行を行います：

1. **環境設定の読み込み**:
   - 環境変数ファイルからの設定読み込み

2. **仮想環境の有効化**:
   - Python仮想環境を有効化（PowerShellの場合）:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **ブラウザの初期化**:
   - Seleniumの標準インターフェースを使用してブラウザを初期化

4. **ログイン実行**:
   - ログイン関数を呼び出し、成功/失敗を確認

5. **CSVダウンロード**:
   - ログイン成功後、CSVダウンロード関数を呼び出し
   - ダウンロードしたファイルのパスを取得

6. **ブラウザの終了**:
   - 処理完了後にブラウザを確実に終了

### 5.1. モジュールとしての実行方法

仮想環境内で以下のようにモジュールとして実行します：

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# ログインモジュールをテスト実行
python -m src.modules.ebis.login_page

# CSVダウンロードモジュールを実行
python -m src.modules.ebis.csv_downloader --start "2024-01-01" --end "2024-01-31"
```

PowerShellで複数のコマンドを連続実行する場合は、`&&`ではなく`;`を使用します：

```powershell
cd C:\dev\CODE\ebis_bq ; python -m src.modules.ebis.login_page
```

## 6. 開発ガイドライン

### 6.1. コード実装のポイント

1. **シンプルさの維持**:
   - 複雑な抽象化は避け、直接的で理解しやすいコードを書く
   - メソッドや関数は一つの責任だけを持つようにする
   - 不要な処理やエラーハンドリングを避ける

2. **ブラウザ操作**:
   - Browserクラスのカスタムメソッドを使わず、Seleniumの基本APIを直接使用する
   - 標準的な要素検索・操作メソッドを使用する
   - 複雑なラッパーメソッドではなく、短い待機時間と明示的なエラーハンドリングを使用する

3. **エラー処理**:
   - try-exceptブロックで具体的な処理を囲み、個別にエラーをハンドリングする
   - エラーメッセージは具体的で解決可能な内容にする
   - 各操作の成功/失敗状態を明確に記録する

### 6.2. 避けるべきパターン

1. **複雑なクラス階層**:
   - 多層の継承関係は避ける
   - 汎用クラスよりも、具体的なユースケース向けの関数を好む

2. **過剰な抽象化**:
   - セレクタ管理などの抽象化レイヤーは最小限にする
   - カスタムラッパーメソッドに依存せず、標準APIを使用する

3. **過剰なエラーハンドリング**:
   - リトライロジックや複雑な検証処理は必要最小限にする
   - シンプルなエラーチェックと明確なメッセージを優先する

## 7. 実行例

以下は、コマンドラインからCSVダウンロード機能を実行する例です：

```powershell
# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 詳細分析レポートCSVダウンロードモジュールを実行
python -m src.modules.ebis.csv_downloader --type detailed_analysis --start "2024-01-01" --end "2024-01-31"

# コンバージョン属性レポートCSVダウンロードモジュールを実行
python -m src.modules.ebis.csv_downloader --type cv_attribute --start "2024-01-01" --end "2024-01-31"
```

CSVダウンロード機能の実行結果として、以下のようなファイルが生成されます：
- 詳細分析レポート: `data/downloads/YYYYMMDD_ebis_detailed_report.csv`
- コンバージョン属性レポート: `data/downloads/YYYYMMDD_ebis_CVrepo.csv`
- ファイル形式: UTF-8またはSJISエンコーディングのCSV
- ファイル内容: 
  - A列に「日付」列が追加され、データ行には前日の日付（YYYY-MM-DD形式）が挿入されます
  - 元のEBiSレポートデータはB列以降に配置されます

あるいは、Pythonスクリプト内での使用例：

```python
from src.modules.ebis.csv_downloader import EbisCSVDownloader
from selenium import webdriver
from src.utils.environment import env
from src.modules.ebis.login_page import login

# 環境変数の読み込み
env.load_env()

# ブラウザの初期化
browser = webdriver.Chrome()

try:
    # ログイン実行
    if login(browser):
        # CSVダウンローダーの初期化
        downloader = EbisCSVDownloader(browser)
        
        # 詳細分析レポートのCSVダウンロード
        detailed_csv = downloader.download_csv(
            csv_type="detailed_analysis",
            start_date="2024-01-01",
            end_date="2024-01-31",
            traffic_type="all"
        )
        
        # コンバージョン属性レポートのCSVダウンロード
        cv_attribute_csv = downloader.download_cv_attribute_csv(
            start_date="2024-01-01",
            end_date="2024-01-31",
            traffic_type="all"
        )
        
        if detailed_csv and cv_attribute_csv:
            print(f"詳細分析レポートダウンロード成功: {detailed_csv}")
            print(f"コンバージョン属性レポートダウンロード成功: {cv_attribute_csv}")
        else:
            print("ダウンロード失敗")
finally:
    browser.quit()
```

## 8. 要素識別情報

### 8.1. セレクタファイルの使用

要素識別情報は、`config/selectors.csv`ファイルで一元管理されています。このファイルには、各要素のセレクタ情報が以下の形式で定義されています：

```csv
group,name,selector_type,selector_value,description
```

各フィールドの説明：
- `group`: 要素のグループ（例: login, detailed_analysis, cv_attribute）
- `name`: 要素の識別名
- `selector_type`: セレクタの種類（xpath, css, id）
- `selector_value`: 実際のセレクタ値
- `description`: 要素の説明

### 8.2. セレクタの取得と要素操作

セレクタの取得と要素操作は以下のように行います：

```python
# セレクタの取得
selector = self.browser.get_selector(group_name, element_name)
if not selector:
    raise CSVDownloadError(f"{element_name}のセレクタが見つかりません")

# セレクタタイプに応じたBy定数の選択
selector_type = selector['selector_type'].lower()
by = self._get_by_type(selector_type)

# 要素の待機と取得
try:
    # 明示的な待機を使用して要素を取得
    element = WebDriverWait(self.driver, self.element_timeout).until(
        EC.presence_of_element_located((by, selector['selector_value']))
    )
    
    # 要素が表示されるまで待機
    element = WebDriverWait(self.driver, self.element_timeout).until(
        EC.visibility_of_element_located((by, selector['selector_value']))
    )
    
    # 要素が操作可能になるまで待機（クリック操作の場合）
    element = WebDriverWait(self.driver, self.element_timeout).until(
        EC.element_to_be_clickable((by, selector['selector_value']))
    )
    
    # 要素までスクロール
    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
    
    # スクリーンショットを取得（操作前）
    self.browser.save_screenshot(f"before_{element_name}_operation.png")
    
    try:
        # 通常のクリック操作を試行
        element.click()
    except Exception as click_error:
        self.logger.warning(f"通常のクリック操作に失敗: {click_error}")
        # JavaScriptによるクリックを試行
        self.driver.execute_script("arguments[0].click();", element)
    
    # スクリーンショットを取得（操作後）
    self.browser.save_screenshot(f"after_{element_name}_operation.png")
    
except TimeoutException:
    self.logger.error(f"{element_name}の要素が見つからないかクリック不可: タイムアウト")
    self.browser.save_screenshot(f"error_{element_name}_timeout.png")
    raise CSVDownloadError(f"{element_name}の要素が見つかりません")
    
except Exception as e:
    self.logger.error(f"{element_name}の操作中にエラー: {str(e)}")
    self.browser.save_screenshot(f"error_{element_name}_operation.png")
    # HTMLソースを保存
    with open(f"error_{element_name}_source.html", "w", encoding="utf-8") as f:
        f.write(self.driver.page_source)
    raise CSVDownloadError(f"{element_name}の操作に失敗: {str(e)}")
```

### 8.3. 定義済みセレクタグループ

#### 8.3.1. ログインページ要素 (group="login")

| name | selector_type | description |
|------|--------------|-------------|
| account_key | id | アカウントキー入力欄 |
| username | id | ユーザー名入力欄 |
| password | id | パスワード入力欄 |
| login_button | css | ログインボタン |

#### 8.3.2. 詳細分析ページ要素 (group="detailed_analysis")

| name | selector_type | description |
|------|--------------|-------------|
| all_traffic_tab | xpath | 全トラフィックタブ |
| date_picker_trigger | xpath | 日付カレンダーを開くボタン |
| start_date_input | xpath | 開始日入力フィールド |
| end_date_input | xpath | 終了日入力フィールド |
| apply_button | xpath | 適用ボタン |
| import_button | xpath | インポートボタン |
| download_button | xpath | ダウンロードボタン |
| view_button | css | ビューボタン |
| program_all_view | css | プログラム用全項目ビュー |

#### 8.3.3. CV属性ページ要素 (group="cv_attribute")

| name | selector_type | description |
|------|--------------|-------------|
| csv_button | xpath | CSVボタン |
| date_picker_trigger | xpath | 日付範囲選択ボタン |
| start_date_input | xpath | 開始日入力欄 |
| end_date_input | xpath | 終了日入力欄 |
| apply_button | xpath | 日付適用ボタン |
| all_traffic_tab | xpath | 全トラフィックタブ |
| download_button | xpath | ダウンロードボタン |

### 8.4. セレクタファイルの管理

セレクタファイルの管理に関する重要な注意点：

1. **一元管理の原則**:
   - すべての要素識別情報は`selectors.csv`で管理
   - コード内でのハードコーディングを避ける
   - UIの変更時は`selectors.csv`のみを更新

2. **セレクタの優先順位**:
   - ID > CSS > XPathの順で優先的に使用
   - 動的に生成される要素に対しては、より安定したセレクタを選択

3. **メンテナンス**:
   - 定期的なセレクタの有効性確認
   - UIの変更に応じた迅速な更新
   - 変更履歴の管理

4. **エラーハンドリング**:
   - セレクタが見つからない場合の適切なエラーメッセージ
   - スクリーンショットの保存による問題の可視化
   - 代替セレクタの提供（可能な場合）

### 8.5. セレクタ使用のベストプラクティス

1. **要素の待機と取得**:
```python
def wait_and_get_element(self, group_name: str, element_name: str, clickable: bool = False) -> WebElement:
    """
    要素を待機して取得する
    
    Args:
        group_name: セレクタのグループ名
        element_name: 要素の名前
        clickable: クリック可能な状態まで待機するかどうか
        
    Returns:
        WebElement: 取得した要素
        
    Raises:
        CSVDownloadError: 要素の取得に失敗した場合
    """
    selector = self.browser.get_selector(group_name, element_name)
    if not selector:
        raise CSVDownloadError(f"{element_name}のセレクタが見つかりません")
        
    by = self._get_by_type(selector['selector_type'])
    try:
        # まず要素の存在を待機
        element = WebDriverWait(self.driver, self.element_timeout).until(
            EC.presence_of_element_located((by, selector['selector_value']))
        )
        
        # 要素が表示されるまで待機
        element = WebDriverWait(self.driver, self.element_timeout).until(
            EC.visibility_of_element_located((by, selector['selector_value']))
        )
        
        # クリック可能な状態まで待機（オプション）
        if clickable:
            element = WebDriverWait(self.driver, self.element_timeout).until(
                EC.element_to_be_clickable((by, selector['selector_value']))
            )
            
        return element
        
    except TimeoutException as e:
        self.logger.error(f"{element_name}の要素待機中にタイムアウト")
        self.browser.save_screenshot(f"error_{element_name}_timeout.png")
        raise CSVDownloadError(f"{element_name}の要素が見つかりません") from e
        
    except Exception as e:
        self.logger.error(f"{element_name}の要素取得中にエラー: {str(e)}")
        self.browser.save_screenshot(f"error_{element_name}_get.png")
        raise CSVDownloadError(f"{element_name}の要素取得に失敗: {str(e)}") from e
```

2. **安定的なクリック操作**:
```python
def safe_click(self, element: WebElement, element_name: str) -> bool:
    """
    安定的なクリック操作を実行する
    
    Args:
        element: クリックする要素
        element_name: 要素の名前（ログ用）
        
    Returns:
        bool: クリックが成功した場合はTrue
    """
    try:
        # スクロール処理
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)  # スクロールの完了を待機
        
        # クリック前のスクリーンショット
        self.browser.save_screenshot(f"before_{element_name}_click.png")
        
        try:
            # 通常のクリック
            element.click()
        except Exception as click_error:
            self.logger.warning(f"通常のクリックに失敗: {click_error}")
            # JavaScriptクリック
            self.driver.execute_script("arguments[0].click();", element)
            
        # クリック後のスクリーンショット
        self.browser.save_screenshot(f"after_{element_name}_click.png")
        return True
        
    except Exception as e:
        self.logger.error(f"{element_name}のクリック操作に失敗: {str(e)}")
        self.browser.save_screenshot(f"error_{element_name}_click.png")
        return False
```

3. **エラー処理とリカバリ**:
```python
try:
    # 要素の取得
    element = self.wait_and_get_element(group_name, element_name, clickable=True)
    
    # クリック操作の実行
    if not self.safe_click(element, element_name):
        # 代替手段を試行
        self.logger.info(f"{element_name}の代替クリック手段を試行")
        try:
            # ActionChainsを使用
            ActionChains(self.driver).move_to_element(element).click().perform()
        except Exception as action_error:
            self.logger.error(f"ActionChainsによるクリックも失敗: {action_error}")
            raise CSVDownloadError(f"{element_name}のクリック操作に失敗")
            
except Exception as e:
    self.logger.error(f"要素操作に失敗: {str(e)}")
    # エラー情報の保存
    self.browser.save_screenshot(f"error_{element_name}_operation.png")
    with open(f"error_{element_name}_source.html", "w", encoding="utf-8") as f:
        f.write(self.driver.page_source)
    raise CSVDownloadError(str(e))
```

## 9. 用語定義

- **要素ID**: HTML要素の識別子となるid属性の値
- **CSSセレクタ**: CSS構文を使用して要素を特定するための文字列
- **XPath**: XML Path Languageに基づく要素の位置を示す式
- **ドライバー**: Seleniumがブラウザを操作するためのインターフェース
- **仮想環境**: プロジェクト固有のPythonパッケージをインストールする独立した環境

## 10. 参考情報

### 10.1. 環境変数ファイル例

`config/secrets.env`:
```
EBIS_ACCOUNT_KEY=<アカウントキー>
EBIS_USERNAME=<ユーザー名>
EBIS_PASSWORD=<パスワード>
```

### 10.2. 設定ファイル例

`config/settings.ini`:
```
[LOGIN]
url=https://id.ebis.ne.jp/
element_timeout=5
redirect_timeout=10
max_attempts=2
success_url=https://id.ebis.ne.jp/dashboard

[CSV_DOWNLOAD]
download_dir=data/downloads
analysis_url=https://id.ebis.ne.jp/xxxx/analysis
element_timeout=5
download_timeout=60
page_load_wait=1
```

### 10.3. 必要なパッケージ

`requirements.txt`:
```
selenium==4.15.2
webdriver-manager==4.0.1
python-dotenv==1.0.0
pytest==7.4.3
```