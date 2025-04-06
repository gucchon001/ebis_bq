# テスト実行ガイド

このドキュメントでは、本プロジェクトのテスト方法について説明します。

## テスト概要

本プロジェクトには以下の種類のテストが含まれています：

1. **モックテスト** - 実際のAPIや外部サービスに接続せずにテストを行います
2. **実接続テスト** - 実際のGitリポジトリやOpenAI APIに接続してテストを行います

## 前提条件

- Python 3.7以上
- 仮想環境（venv）でのセットアップ推奨
- `pip install -r requirements.txt` で依存ライブラリをインストール済み
- Git がインストールされていること
- （実接続テスト用）OpenAI APIキーを取得していること

## テストの実行方法

### モックテストの実行

```bash
# すべてのテストを実行
python -m pytest tests/

# 特定のテストファイルを実行
python -m pytest tests/test_git_batch.py
python -m pytest tests/test_git_integration.py
python -m pytest tests/test_openai_git_helper.py

# 特定のテストケースを実行
python -m pytest tests/test_git_batch.py::TestGitBatchProcessor::test_git_status
```

### 実接続テストの実行

実際のGitリポジトリとOpenAI APIに接続してテストを行うには、環境変数を設定する必要があります。

#### 環境変数の設定

Windows PowerShellの場合:

```powershell
# OpenAI APIキーを設定
$env:OPENAI_API_KEY = "your_api_key_here"

# テスト対象のGitリポジトリパスを設定（任意、デフォルトはカレントディレクトリ）
$env:TEST_REPO_PATH = "C:\path\to\your\git\repo"

# OpenAI APIテストをスキップする場合（任意）
$env:SKIP_OPENAI_TESTS = "true"
```

#### 専用ヘルパースクリプトによる実行

実接続テストを簡単に実行するためのヘルパースクリプトが用意されています：

```bash
# すべての実接続テストを実行
python run_real_tests.py --test-path=./git_test

# OpenAI APIテストをスキップして実行
python run_real_tests.py --test-path=./git_test --skip-openai

# 特定のテストケースのみを実行
python run_real_tests.py --test-path=./git_test --test-name=test_git_status_on_real_repo
```

## テストの説明

### 実接続テスト (`test_real_integration.py`)

実際のGitリポジトリとOpenAI APIに接続してテストを行います。

テストケース:
- `test_find_real_git_repos` - Gitリポジトリの検索機能をテスト
- `test_git_status_on_real_repo` - Gitステータス取得機能をテスト
- `test_git_commit_on_real_repo` - Git変更のコミット機能をテスト
- `test_generate_commit_message_with_real_api` - OpenAI APIを使用したコミットメッセージ生成機能をテスト（OpenAI API必須）
- `test_check_sensitive_info_with_real_api` - OpenAI APIを使用した機密情報チェック機能をテスト（OpenAI API必須）
- `test_analyze_code_quality_with_real_api` - OpenAI APIを使用したコード品質分析機能をテスト（OpenAI API必須）

**注意**: OpenAI APIを使用するテストは、APIキーが必要で、また課金が発生する可能性があります。`--skip-openai`オプションを使用するか、`SKIP_OPENAI_TESTS=true`環境変数を設定することでスキップできます。

## 既知の問題と対処法

1. **PermissionError（一時ディレクトリの削除エラー）**
   - 症状: テスト終了時に一時ディレクトリの削除に失敗する
   - 対処: リトライロジックを実装済み。解決しない場合は手動で削除してください

2. **UnicodeDecodeError（文字エンコーディングエラー）**
   - 症状: Gitコマンド実行時や、ファイル読み込み時にエンコーディングエラーが発生
   - 対処: すべての`subprocess.run`と`open`に`encoding='utf-8'`と`errors='replace'`パラメータを追加済み

3. **オンラインテスト接続エラー**
   - 症状: インターネット接続がない場合や、APIキーが無効な場合にテストが失敗
   - 対処: ネットワーク接続とAPIキーの有効性を確認してください

## テスト改善のポイント

- [ ] テストカバレッジの向上
- [ ] 並列テスト実行の導入
- [ ] CIパイプラインへの統合
- [x] テスト時の一時ファイル処理の改善
- [x] エンコーディング問題の解決
- [x] エラーハンドリングの強化

## フィードバックと貢献

テスト実行中に問題が発生した場合や、改善案がある場合は、Issueを作成するか、プルリクエストを送ってください。 