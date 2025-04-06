## 11. CSVファイル処理機能

### 11.1 概要
CSVファイルを読み込み、データ型を推論してスキーマ情報をJSON形式で出力する機能を提供します。
設定ファイル (settings.ini) から各種パラメータを取得して動作し、データ型の整合性チェックも行います。

### 11.2 機能詳細

#### 11.2.1 CSVファイルパスの設定
- 設定ファイル（`settings.ini`）の `CSV_FILES` セクションでファイルパスを管理
- 一元化されたCSVフォルダパス (`CSV_PATH`) で管理
  ```ini
  [CSV_FILES]
  # CSVファイルパス設定
  CSV_PATH = data/csv/
  ```

#### 11.2.2 文字コード判定
- 最初の10行のデータを使用して効率的に文字コードを判定
- CP932（SJIS）とUTF-8の両エンコーディングに対応
- `chardet`ライブラリを使用して文字コードを自動検出し、確度も出力
- 確度が低い場合（70%未満）はデフォルトエンコーディングを使用

#### 11.2.3 ファイルの読み込みとプレビュー
- ファイルのヘッダー行と内容を読み込み
- 最初の5行をログに出力してデータプレビューを提供
- エンコーディングエラー発生時は代替エンコーディングで再試行

#### 11.2.4 ヘッダー行の取得
- デフォルトでは1行目をヘッダー行として扱う
- ヘッダー行の位置は設定ファイルで変更可能
  ```ini
  # ヘッダー行の位置 (デフォルト1行目)
  HEADER_ROW = 1
  ```

#### 11.2.5 データの読み込みとレコード数計算
- pandasを使用してCSVデータを読み込み、データフレームとして処理
- 読み込まれたレコード数を計算して返却

#### 11.2.6 データ型の推論
次の6種類のデータ型を自動推論
- `STR`: 文字列型
- `INT`: 整数型
- `FLOAT`: 浮動小数点数型（小数点を含む数値、科学技術表記、桁区切りカンマ対応）
- `DATE`: 日付型（YYYY/MM/DD, YYYY-MM-DD）
- `TIMESTAMP`: 日時型（日付+時間）
- `BOOLEAN`: 真偽値型

#### 11.2.7 データ型の整合性チェック
- 推論されたデータ型と実際のデータの整合性をチェック
- 推論された型と異なる値がある場合、その割合と実例を記録
- 整合性が90%未満の列は警告ログを出力
- 整合性チェック結果は別ファイルとして保存

#### 11.2.8 スキーマの生成と保存
- スキーマ情報をJSON形式で生成し、指定されたディレクトリに保存
- スキーマJSONには以下の項目を含む
  ```json
  [
    {
      "COLUMN_ORIGIN_NAME": "列の元の名前（ヘッダー行の値）",
      "DATA_TYPE": "推論されたデータ型",
      "COLUMN_AFTER_NAME": "変換後の列名（将来の拡張用）",
      "DESCRIPTION": "列の説明（将来の拡張用）"
    },
    ...
  ]
  ```
- **重要**: すべてのフィールドは省略せずに保持する必要があります
  - `COLUMN_ORIGIN_NAME`: 元の列名（CSV上の名前）
  - `DATA_TYPE`: 推論されたデータ型（STR, INT, FLOAT, DATE, TIMESTAMP, BOOLEAN）
  - `COLUMN_AFTER_NAME`: データ変換後に使用する列名（空でも必ず保持）
  - `DESCRIPTION`: 列の説明文（空でも必ず保持）

### 11.3 使用方法

#### 11.3.1 ライブラリとしての使用
```python
from src.modules.csv_processor import CSVProcessor

# CSVProcessorのインスタンス作成
processor = CSVProcessor()

# CSVファイル処理（パスを指定）
result = processor.process_csv_file('path/to/your/file.csv')

# 結果の取得
headers = result['headers']       # ヘッダー行
data = result['data']             # データ行
record_count = result['record_count']  # レコード数
schema = result['schema']         # 生成されたスキーマ
schema_path = result['schema_path']    # 保存されたスキーマファイルのパス
consistency_results = result['consistency_results']  # データ型整合性チェック結果
```

#### 11.3.2 コマンドラインからの実行
```bash
# 基本的な使用方法
python -m src.modules.csv_processor data.csv

# エンコーディングを指定
python -m src.modules.csv_processor data.csv --encoding utf-8

# ヘッダー行の位置を指定
python -m src.modules.csv_processor data.csv --header-row 2

# settings.iniのデフォルト設定を使用
python -m src.modules.csv_processor --use-default
```

### 11.4 設定項目
| 設定項目         | 説明                              | デフォルト値     |
|------------------|----------------------------------|----------------|
| CSV_PATH         | CSVファイルの格納パス              | data/csv/      |
| DEFAULT_ENCODING | デフォルトのエンコーディング        | cp932          |
| HEADER_ROW       | ヘッダー行の位置                   | 1              |
| SCHEMA_DIR       | スキーマJSONファイルの保存先        | data/csv/schema/|
| DEFAULT_CSV_FILE | デフォルトで処理するCSVファイル名   | (空)           |

### 11.5 出力ファイル
処理結果として2種類のJSONファイルが生成されます：

1. **スキーマファイル** (`<ファイル名>_schema.json`)
   - 各列の名前とデータ型の対応
   - 将来の拡張用フィールドを含む

2. **整合性チェック結果ファイル** (`<ファイル名>_consistency.json`)
   - 各列のデータ型整合性の評価結果
   - 整合性の低い値のサンプル（最大10件）
   - 整合性の低い値が出現する行番号

### 11.6 エラー処理
- ファイルが存在しない場合: `FileNotFoundError`
- エンコーディングエラー: 代替エンコーディングで再試行
- 文字コード検出失敗: デフォルトエンコーディングを使用
- データ型整合性が低い場合: 警告ログを出力
- その他のエラー: 例外を発生させ、詳細なエラーログを出力

### 11.7 拡張性
- `COLUMN_AFTER_NAME`と`DESCRIPTION`フィールドは将来の拡張用に予約
- データ型の定義は拡張可能な構造になっており、新しいタイプを追加可能 