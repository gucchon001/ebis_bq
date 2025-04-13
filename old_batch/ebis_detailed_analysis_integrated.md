# アドエビス詳細分析ページ CSVダウンロード機能 仕様書

## 1. 概要
アドエビスの詳細分析ページからCSVデータを自動ダウンロードする機能を提供します。

### 目的
- データエクスポート作業の自動化
- 作業効率の向上

### 動作環境
- Python 3.9以上
- Chrome/Chromium ブラウザ
- Windows 10以上

### モジュール構成
```
src/modules/
├── ebis/
│   ├── __init__.py
│   ├── browser.py          # Ad Ebis用ブラウザ機能 (selenium.browser.Browserを継承)
│   ├── login_page.py       # Ad Ebisログイン機能 (selenium.login_page.LoginPageを継承)
│   └── report_downloader.py # 詳細分析レポートダウンロード機能
└── selenium/
    ├── __init__.py
    ├── browser.py          # 汎用ブラウザ基本機能
    ├── login_page.py       # 汎用ログインページ操作
    └── page_analyzer.py    # 汎用ページ解析機能
```

## 2. 基本設定

### 2.1 設定ファイル構成

1.  **セレクタ定義** (`config/selectors.csv`)
    - すべての機能で使用するセレクタを一元管理します。
    ```csv
    group,name,selector_type,selector_value,description
    ebis_login,account_key,id,account_key,アカウントキー入力欄
    ebis_login,username,id,username,ユーザー名入力欄
    ebis_login,password,id,password,パスワード入力欄
    ebis_login,submit,css,.loginbtn,ログインボタン
    analysis,date_from,id,date_from,開始日入力欄
    analysis,date_to,id,date_to,終了日入力欄
    analysis,search_btn,css,.search-button,検索ボタン
    analysis,download_btn,css,.download-csv,CSVダウンロードボタン
    dashboard,welcome_message,css,.welcome-message,ログイン成功時のウェルカムメッセージ
    ```

2.  **環境設定** (`config/settings.ini`)
```ini
    [EBIS]
    dashboard_url = https://bishamon.ebis.ne.jp/dashboard
    analysis_url = https://bishamon.ebis.ne.jp/analysis
    download_dir = data/csv

[BROWSER]
headless = true
    timeout = 10
    page_load_timeout = 30
    redirect_timeout = 10
    retry_count = 3
    screenshot_on_error = true
screenshot_dir = logs/screenshots

[LOGIN]
url = https://id.ebis.ne.jp/
success_url = https://bishamon.ebis.ne.jp/dashboard
    success_element_group = dashboard
    success_element_name = welcome_message
    max_attempts = 3
    ```

3.  **認証情報** (`config/secrets.env`)
    - `.gitignore`に追加し、バージョン管理から除外します。
```env
EBIS_USERNAME=your_username
EBIS_PASSWORD=your_password
EBIS_ACCOUNT_KEY=your_account_key
```

### 2.2 共通ユーティリティ
- 環境変数・設定ファイル読み込み: `src/utils/environment.py`
- ロギング設定: `src/utils/logging_config.py`
- Slack通知 (オプション): `src/utils/slack_notifier.py`

## 3. 処理フロー (ステップバイステップ)

### Step 1: 初期化
1.  **設定読み込み**: `environment.py` を使用して `settings.ini` と `secrets.env` から設定値を読み込みます。
2.  **ロガー設定**: `logging_config.py` でロガーを初期化します。
3.  **ブラウザ初期化**: `EbisBrowser` クラスをインスタンス化し、`setup()` メソッドを呼び出してChromeドライバーを準備します。
    - `headless`, `timeout` などの設定は `settings.ini` から読み込みます。
    - `selectors.csv` を自動的に読み込みます。
4.  **ページオブジェクト初期化**: `EbisLoginPage` と `ReportDownloader` を `EbisBrowser` インスタンスを渡して初期化します。

### Step 2: Ad Ebis ログイン
1.  **ログインページ移動**: `EbisLoginPage.navigate_to_login_page()` で `settings.ini` の `[LOGIN]url` へ移動します。
2.  **ページロード待機**: `EbisBrowser.wait_for_page_load()` でページの読み込み完了を待ちます。
3.  **アカウントキー認証 (必要な場合)**:
    - `EbisLoginPage` 内でアカウントキー入力欄 (`ebis_login`, `account_key` セレクタ) を検出し、`secrets.env` の `EBIS_ACCOUNT_KEY` を入力して送信します。
    - リダイレクト完了 (`EbisBrowser.wait_for_login_redirect()`) を待ちます。
4.  **ユーザー認証**:
    - `EbisLoginPage.fill_login_form()` でユーザー名 (`ebis_login`, `username`) とパスワード (`ebis_login`, `password`) を入力します。
    - `EbisLoginPage.submit_login_form()` でログインボタン (`ebis_login`, `submit`) をクリックします。
5.  **ログイン成功判定**:
    - `EbisLoginPage.check_login_result()` で以下の条件を確認します:
        - 現在のURLが `settings.ini` の `[LOGIN]success_url` を含むか？
        - ログイン成功要素 (`settings.ini` の `success_element_group`, `success_element_name` で指定されたセレクタ) が表示されるか？
        - エラーメッセージ要素が表示されていないか？
    - 判定失敗時は、`settings.ini` の `[LOGIN]max_attempts` 回までリトライします。
6.  **エラー処理**:
    - 認証失敗: リトライ上限に達したらエラーログを出力し、処理を中断します。
    - タイムアウト/要素未検出: エラーログとスクリーンショットを出力し、リトライします。

### Step 3: 詳細分析レポート CSV ダウンロード
1.  **詳細分析ページ移動**: `ReportDownloader.navigate_to_analysis_page()` で `settings.ini` の `[EBIS]analysis_url` へ移動します。
2.  **ページロード待機**: `EbisBrowser.wait_for_page_load()` でページの読み込み完了を待ちます。
3.  **検索条件設定**: `ReportDownloader.set_search_conditions()` で日付範囲 (`analysis`, `date_from`, `analysis`, `date_to` セレクタ) を指定し、検索ボタン (`analysis`, `search_btn`) をクリックします。
4.  **結果表示待機**: 検索結果が表示されるのを待ちます (特定の要素やデータテーブルの表示を確認)。
5.  **CSVダウンロード実行**: `ReportDownloader.execute_download()` でダウンロードボタン (`analysis`, `download_btn`) をクリックします。
6.  **ダウンロード完了待機**: `ReportDownloader.wait_for_download()` で `settings.ini` の `[EBIS]download_dir` に指定された形式のファイルが生成されるのを待ちます。
7.  **ファイル検証 (オプション)**: `ReportDownloader.validate_downloaded_file()` でダウンロードされたCSVファイルの内容を簡易的に検証します (ヘッダー行、データ行の存在確認など)。
8.  **エラー処理**:
    - ページ遷移失敗: セッション切れの可能性を考慮し、再ログインから試行します。
    - 要素未検出: タイムアウト値を調整するか、セレクタを見直します。
    - ダウンロード失敗/ファイル未検出: リトライ処理を実行します。

### Step 4: 後処理
1.  **ファイルリネーム/移動**: 必要に応じて、ダウンロードしたCSVファイル名を標準化し、指定のディレクトリへ移動します。
2.  **ログアウト (推奨)**: 可能であれば、`EbisBrowser` にログアウト機能を追加し、実行します。
3.  **ブラウザ終了**: `EbisBrowser.quit()` でブラウザプロセスを終了します。
4.  **結果通知 (オプション)**: 処理結果 (成功/失敗、ダウンロードファイルパスなど) をログに出力し、必要であれば `slack_notifier.py` で通知します。

## 4. エラー対応ガイドライン

### 4.1 一般的なエラーパターン
1.  **ネットワーク接続**: 接続が不安定な場合、タイムアウトが発生しやすくなります。
2.  **認証情報誤り**: `secrets.env` の情報が古い、または間違っている可能性があります。
3.  **要素セレクタ変更**: Ad Ebis側のUI変更により、`selectors.csv` のセレクタが動作しなくなることがあります。
4.  **タイムアウト**: ネットワーク遅延やAd Ebis側のサーバー負荷により、処理時間が設定値を超えることがあります。
5.  **予期せぬポップアップ/アラート**: ログイン後などに予期せぬ通知が表示され、操作を妨げることがあります。

### 4.2 対処方針
1.  **ログ確認**: まず `logs/ebis_download.log` を確認し、エラー発生箇所とメッセージを特定します。
2.  **スクリーンショット確認**: エラー発生時に `logs/screenshots` に保存された画像を確認し、画面の状態を把握します。
3.  **設定ファイル確認**: `settings.ini`, `secrets.env`, `selectors.csv` の内容が正しいか確認します。
4.  **手動操作確認**: 同じ操作を手動で行い、問題が再現するか確認します。
5.  **タイムアウト調整**: `settings.ini` のタイムアウト値を一時的に増やして再試行します。
6.  **セレクタ検証**: 開発者ツールでHTML構造を確認し、`selectors.csv` のセレクタを修正します。

## 5. 運用管理

### 5.1 ログ管理
- ログファイル: `logs/ebis_download.log`
- ログレベル: `settings.ini` の `[development]` または `[production]` セクションで設定 (通常は `INFO`、デバッグ時は `DEBUG`)
- ログローテーション: 必要に応じて `logging_config.py` で設定 (例: 日次ローテーション、最大ファイルサイズなど)
- 保持期間: 定期的に古いログファイルを削除する運用を検討します (例: 30日以上経過したファイルを削除)。

### 5.2 定期メンテナンス
- **セレクタ検証 (月1回推奨)**: Ad EbisのUI変更がないか定期的に確認し、必要であれば `selectors.csv` を更新します。
- **ログ確認 (週1回推奨)**: 定期的にログを確認し、エラーや警告がないかチェックします。
- **認証情報更新**: パスワード変更時などは速やかに `secrets.env` を更新します。

## 6. 注意事項
- **実行時間**: Ad Ebisの利用規約やサーバー負荷を考慮し、業務時間外や深夜帯での実行を推奨します。
- **大量データ**: 一度に大量のデータをダウンロードすると、タイムアウトやサーバー負荷の原因となるため、期間を分割して実行するなどの対策を検討します。
- **エラー監視**: 処理失敗時に確実に検知できるよう、ログ監視や通知の仕組みを整備します。
- **バックアップ**: `config` ディレクトリやダウンロードしたデータは定期的にバックアップを取得します。
- **依存関係**: 使用するライブラリ (`selenium`, `webdriver-manager` など) のバージョン互換性に注意し、`requirements.txt` で管理します。

## 7. 補足情報

### 7.1 出力ファイル形式
- ファイル名: `YYYYMMDD_ebis_detailed_report.csv` (命名規則は `report_downloader.py` で調整可能)
- 文字コード: UTF-8 (Ad Ebisの出力に依存、必要なら変換処理を追加)
- 区切り文字: カンマ（,）

### 7.2 実行オプション一覧 (実装する場合)
- スクリプト実行時にコマンドライン引数で動作を変更できるようにします。
  ```bash
  python src/main.py --date 2024-04-10 # 単一日付指定
  python src/main.py --start-date 2024-04-01 --end-date 2024-04-10 # 期間指定
  python src/main.py --output-dir /path/to/output # 出力先指定
  python src/main.py --no-headless # ブラウザ表示モード
  python src/main.py --debug # デバッグログ出力
  ```

## 8. 用語解説
- **セレクタ**: Webページ上のHTML要素を特定するための識別子 (例: ID, CSSクラス, XPath)。
- **ヘッドレスモード**: ブラウザのGUIを表示せずにバックグラウンドで実行するモード。
- **タイムアウト**: 処理が完了するまで待機する最大時間。
- **ページオブジェクトモデル (POM)**: Webページの各要素と操作をクラスとしてモデル化する設計パターン。保守性と再利用性を高めます。