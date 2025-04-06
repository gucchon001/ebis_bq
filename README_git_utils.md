# Git関連ユーティリティ

このプロジェクトには、Git操作を支援する2つの主要なユーティリティモジュールが含まれています：

1. **Git一括管理ツール** (`src/utils/git_batch.py`) - 複数のGitリポジトリに対する一括操作
2. **OpenAI Gitヘルパー** (`src/utils/openai_git_helper.py`) - OpenAI APIを活用したGit操作の強化

## 機能概要

### Git一括管理ツール

複数のGitリポジトリに対して同じ操作を一括で実行することができます。

**主な機能**:
- 複数リポジトリの一括ステータス確認
- 複数リポジトリの一括プル/プッシュ
- 複数リポジトリの一括コミット
- 複数リポジトリの一括チェックアウト
- 複数リポジトリの一括リセット/クリーン

### OpenAI Gitヘルパー

OpenAI APIを利用してGit操作を強化し、より効率的な開発を支援します。

**主な機能**:
- 変更内容からコミットメッセージを自動生成
- プルリクエストの分析と要約
- コード品質チェック
- 機密情報の漏洩チェック
- 新機能の実装提案

## 使用方法

### Git一括管理ツール

コマンドラインからの使用例:

```bash
# カレントディレクトリ以下のすべてのGitリポジトリの状態を確認
python -m src.utils.git_batch status --recursive

# 特定のディレクトリ以下のGitリポジトリでプル操作を実行
python -m src.utils.git_batch pull --path /path/to/repos --recursive

# コミットメッセージを指定して一括コミット
python -m src.utils.git_batch commit --message "バグ修正: #123" --path /path/to/repos
```

スクリプト内での使用例:

```python
from src.utils.git_batch import execute_git_command

# カレントディレクトリ以下のすべてのGitリポジトリの状態を確認
result = execute_git_command('status', recursive=True)
print(f"総リポジトリ数: {result['summary']['total']}")
print(f"成功: {result['summary']['success']}, 失敗: {result['summary']['failure']}")

# 特定のブランチにチェックアウト
result = execute_git_command('checkout', branch='develop', path='/path/to/repos')

# 一括プッシュ
result = execute_git_command('push', recursive=True, depth=3)
```

### OpenAI Gitヘルパー

コマンドラインからの使用例:

```bash
# 変更内容からAIが生成したコミットメッセージでコミット
python -m src.utils.openai_git_helper ai-commit

# 変更のステージング、コミット、プッシュを一括で実行
python -m src.utils.openai_git_helper ai-full-push

# コード品質分析
python -m src.utils.openai_git_helper analyze-code --file src/main.py

# プルリクエストの分析
python -m src.utils.openai_git_helper analyze-pr --pr-url https://github.com/user/repo/pull/123

# プッシュ前の機密情報漏洩チェック
python -m src.utils.openai_git_helper check-sensitive-info
```

スクリプト内での使用例:

```python
from src.utils.openai_git_helper import OpenAIGitHelper

# ヘルパーインスタンスを作成
helper = OpenAIGitHelper()

# コミットメッセージを自動生成
message = helper.generate_commit_message('/path/to/repo')
print(f"生成されたコミットメッセージ: {message}")

# コード品質をチェック
result = helper.analyze_code_quality('/path/to/repo/src/file.py')
print(f"コード品質の概要: {result['summary']}")
for issue in result['issues']:
    print(f"- 問題: {issue}")

# 機密情報をチェック
check_result = helper.check_sensitive_info('/path/to/repo')
if not check_result['safe']:
    print("機密情報が見つかりました!")
    for issue in check_result['issues']:
        print(f"- {issue['file']}({issue['line']}行目): {issue['type']}")
```

## 統合利用例

Git一括管理ツールとOpenAI Gitヘルパーを組み合わせた使用例:

```python
from src.utils.git_batch import find_git_repos, GitBatchProcessor
from src.utils.openai_git_helper import OpenAIGitHelper

# ディレクトリ内のすべてのGitリポジトリを検索
repos = find_git_repos('/path/to/projects', recursive=True)

# OpenAIヘルパーを初期化
helper = OpenAIGitHelper()

# 各リポジトリに対して実行
for repo in repos:
    # 変更があるかチェック
    processor = GitBatchProcessor([repo])
    status = processor.execute_batch('status')
    
    if "nothing to commit" not in status[repo.name]['output']:
        # 機密情報をチェック
        check_result = helper.check_sensitive_info(repo)
        
        if check_result['safe']:
            # 安全であればAIコミットを実行
            helper.execute_ai_git_command('ai-commit', repo)
            print(f"{repo.name}: AIコミット完了")
        else:
            print(f"{repo.name}: 機密情報が見つかりました！コミットをスキップします")
```

## テスト

テストを実行するには、以下のコマンドを使用します:

```bash
# 単体テストを実行
python -m pytest tests/test_git_batch.py -v
python -m pytest tests/test_openai_git_helper.py -v

# 統合テストを実行
python -m pytest tests/test_git_integration.py -v

# 全テストを実行
python -m pytest tests/test_git*.py -v
```

## 設定

### 環境変数

以下の環境変数を設定できます:

- `OPENAI_API_KEY`: OpenAI APIキー
- `GIT_DEFAULT_BRANCH`: デフォルトのブランチ名（未指定時は現在のブランチを使用）
- `GITHUB_TOKEN`: GitHub API用のトークン（PR分析時に使用）

### 設定ファイル

`config/settings.ini` に以下の設定を追加できます:

```ini
[GIT]
default_branch = main
auto_add = true
use_openai = true

[OPENAI]
model = gpt-3.5-turbo
api_key = 
```

## 注意事項

- 機密情報チェック機能は完璧ではありません。重要なコードをプッシュする前には手動でも確認してください。
- OpenAI API機能を使用するには、有効なAPIキーが必要です。
- 一括操作は慎重に実行してください。特に `reset` や `clean` などの破壊的な操作には注意が必要です。 