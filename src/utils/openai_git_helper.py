#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI APIを利用したGit操作のヘルパー機能

GitコマンドをAIで強化する機能を提供します。
- コミットメッセージの自動生成
- PRの分析と要約
- コード品質チェック
- 新機能の実装支援
"""

import os
import re
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Any, Optional, Union
import subprocess

# 設定管理とロギングのインポート
try:
    from src.utils.environment import env
    from src.utils.logging_config import get_logger
except ImportError:
    # 直接実行時のフォールバック
    import logging
    env = None
    logging.basicConfig(level=logging.INFO)
    get_logger = lambda name: logging.getLogger(name)

# ロガー設定
logger = get_logger(__name__)


class OpenAIGitHelper:
    """OpenAI APIを使用してGit操作を強化するヘルパークラス"""
    
    def __init__(self):
        """初期化処理"""
        # 設定の読み込み
        config_value = self._get_config_value("GIT", "use_openai", "true")
        if isinstance(config_value, bool):
            self.use_openai = config_value
        else:
            self.use_openai = config_value.lower() == "true"
        self.api_key = self._get_config_value("OPENAI", "api_key", os.environ.get("OPENAI_API_KEY", ""))
        self.model = self._get_config_value("OPENAI", "model", "gpt-3.5-turbo")
        
        # APIキーのチェック
        if self.use_openai and not self.api_key:
            logger.warning("OpenAI APIキーが設定されていません。環境変数OPENAI_API_KEYを設定するか、設定ファイルを更新してください。")
            self.use_openai = False
    
    def _get_config_value(self, section: str, key: str, default: str) -> str:
        """設定値を取得する"""
        if env:
            return env.get_config_value(section, key, default)
        return os.environ.get(f"{section}_{key}".upper(), default)
    
    def _run_git_command(self, command: List[str], cwd: str = None, shell: bool = False) -> subprocess.CompletedProcess:
        """Gitコマンドを実行する"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                check=True,
                text=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                shell=shell
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Gitコマンド実行エラー: {e.stderr.strip()}")
            raise
    
    def _call_openai_api(self, messages: List[Dict[str, str]], max_tokens: int = None) -> str:
        """OpenAI APIを呼び出す"""
        if not self.use_openai:
            return "OpenAI APIは無効になっています。設定で有効にしてください。"
        
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("OpenAI APIライブラリがインストールされていません。pip install openai を実行してください。")
            return "OpenAI APIライブラリがインストールされていません。"
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            params = {
                "model": self.model,
                "messages": messages
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API呼び出しエラー: {str(e)}")
            return f"APIエラー: {str(e)}"
    
    def generate_commit_message(self, repo_path: str) -> str:
        """
        変更内容からコミットメッセージを自動生成
        
        Args:
            repo_path: Gitリポジトリのパス
        
        Returns:
            生成されたコミットメッセージ
        """
        if not self.use_openai:
            return "自動生成されたコミットメッセージ (OpenAI API無効)"
        
        logger.info("変更内容からコミットメッセージを生成中...")
        
        try:
            # git diffの実行
            diff_result = self._run_git_command(['git', 'diff', '--staged'], cwd=repo_path)
            diff_output = diff_result.stdout.strip()
            
            if not diff_output:
                return "変更なし"
            
            # diffが大きすぎる場合は要約
            if len(diff_output) > 4000:
                diff_output = diff_output[:4000] + "...(以下省略)"
            
            # ファイル名の一覧を取得
            files_result = self._run_git_command(['git', 'diff', '--staged', '--name-only'], cwd=repo_path)
            files_output = files_result.stdout.strip()
            
            # OpenAI APIでコミットメッセージを生成
            messages = [
                {"role": "system", "content": "あなたはGitコミットメッセージの専門家です。変更内容から簡潔で明確なコミットメッセージを生成してください。"},
                {"role": "user", "content": f"以下のGit変更内容から、適切なコミットメッセージを日本語で作成してください。\n\n"
                                           f"## 変更ファイル:\n{files_output}\n\n"
                                           f"## 変更内容:\n{diff_output}"}
            ]
            
            commit_message = self._call_openai_api(messages, max_tokens=100)
            
            # 余分な記号や改行を削除
            commit_message = commit_message.strip('"\'`')
            commit_message = re.sub(r'^コミットメッセージ[:：]\s*', '', commit_message)
            
            return commit_message
            
        except Exception as e:
            logger.error(f"コミットメッセージ生成エラー: {str(e)}")
            return f"自動生成エラー: {str(e)}"
    
    def analyze_pull_request(self, pr_url: str) -> Dict[str, Any]:
        """
        プルリクエストを分析して要約
        
        Args:
            pr_url: プルリクエストのURL
        
        Returns:
            分析結果の辞書
        """
        if not self.use_openai:
            return {
                "summary": "OpenAI APIが無効なため、PR分析は実行できません。",
                "risks": [],
                "suggestions": []
            }
        
        logger.info(f"プルリクエスト {pr_url} を分析中...")
        
        try:
            # GitHubのPR URLかどうかを確認
            if not (pr_url.startswith("https://github.com/") and "/pull/" in pr_url):
                return {"error": "URLはGitHubのプルリクエストURLである必要があります。"}
            
            # URLからリポジトリ情報とPR番号を抽出
            match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
            if not match:
                return {"error": "PRのURL形式が正しくありません。"}
            
            owner, repo, pr_number = match.groups()
            
            # GitHub APIを使用してPR情報を取得
            try:
                import requests
                
                headers = {}
                github_token = self._get_config_value("GITHUB", "token", os.environ.get("GITHUB_TOKEN", ""))
                if github_token:
                    headers["Authorization"] = f"token {github_token}"
                
                # PRの基本情報を取得
                pr_response = requests.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=headers
                )
                pr_response.raise_for_status()
                pr_data = pr_response.json()
                
                # PRの変更内容を取得（最新のdiff）
                diff_response = requests.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers={**headers, "Accept": "application/vnd.github.v3.diff"}
                )
                diff_response.raise_for_status()
                diff_content = diff_response.text
                
                # 変更が大きすぎる場合は要約
                if len(diff_content) > 4000:
                    diff_content = diff_content[:4000] + "...(以下省略)"
                
                # OpenAI APIでPRを分析
                pr_info = f"""
                タイトル: {pr_data['title']}
                説明: {pr_data['body'] or '説明なし'}
                変更ファイル数: {pr_data['changed_files']}
                追加行数: {pr_data['additions']}
                削除行数: {pr_data['deletions']}
                作成者: {pr_data['user']['login']}
                
                差分:
                {diff_content}
                """
                
                messages = [
                    {"role": "system", "content": "あなたはコードレビューと品質管理の専門家です。プルリクエストを分析し、簡潔に要約して、リスクと改善案を提案してください。"},
                    {"role": "user", "content": f"以下のプルリクエスト情報を分析し、日本語で以下の形式で回答してください：\n\n"
                                              f"1. 概要（PRの目的と主な変更点を簡潔に）\n"
                                              f"2. リスク（潜在的な問題点をリスト形式で）\n"
                                              f"3. 提案（改善点や追加すべきテストなどをリスト形式で）\n\n"
                                              f"{pr_info}"}
                ]
                
                analysis = self._call_openai_api(messages)
                
                # 結果をパースして構造化
                sections = re.split(r"#+\s*|^\d+\.\s+", analysis, flags=re.MULTILINE)
                sections = [s.strip() for s in sections if s.strip()]
                
                result = {
                    "summary": sections[0] if len(sections) > 0 else "分析結果なし",
                    "risks": self._extract_list_items(sections[1]) if len(sections) > 1 else [],
                    "suggestions": self._extract_list_items(sections[2]) if len(sections) > 2 else []
                }
                
                return result
                
            except ImportError:
                return {"error": "requestsライブラリがインストールされていません。pip install requests を実行してください。"}
            except requests.RequestException as e:
                return {"error": f"GitHub APIエラー: {str(e)}"}
            
        except Exception as e:
            logger.error(f"PR分析エラー: {str(e)}")
            return {"error": f"分析エラー: {str(e)}"}
    
    def _extract_list_items(self, text: str) -> List[str]:
        """テキストからリスト項目を抽出"""
        items = re.findall(r"^(?:[-*•]|\d+\.)\s*(.+)$", text, re.MULTILINE)
        if not items:
            # リスト形式でない場合は段落ごとに分割
            items = [p.strip() for p in text.split("\n\n") if p.strip()]
        return items
    
    def analyze_code_quality(self, file_path: str) -> Dict[str, Any]:
        """
        指定されたファイルのコード品質を分析
        
        Args:
            file_path: 分析対象のファイルパス
        
        Returns:
            分析結果の辞書
        """
        if not self.use_openai:
            return {
                "summary": "OpenAI APIが無効なため、コード品質分析は実行できません。",
                "issues": [],
                "suggestions": []
            }
            
        if not os.path.exists(file_path):
            return {"error": f"ファイルが存在しません: {file_path}"}
        
        logger.info(f"ファイル {file_path} のコード品質を分析中...")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                code = f.read()
            
            # ファイルが大きすぎる場合は部分的に分析
            if len(code) > 8000:
                logger.warning(f"ファイルが大きすぎるため、最初の8000文字のみを分析します: {file_path}")
                code = code[:8000] + "\n\n# ... (以下省略) ..."
            
            # ファイル拡張子から言語を推測
            ext = os.path.splitext(file_path)[1].lower()
            language = self._get_language_from_extension(ext)
            
            messages = [
                {"role": "system", "content": f"あなたは{language}のコード品質とベストプラクティスの専門家です。コードを分析し、問題点や改善案を指摘してください。"},
                {"role": "user", "content": f"以下の{language}コードを分析し、日本語で以下の形式で回答してください：\n\n"
                                          f"1. 概要（コードの品質評価を簡潔に）\n"
                                          f"2. 問題点（潜在的な問題をリスト形式で）\n"
                                          f"3. 改善案（具体的な改善案をリスト形式で）\n\n"
                                          f"```{ext[1:]}\n{code}\n```"}
            ]
            
            analysis = self._call_openai_api(messages)
            
            # 結果をパースして構造化
            sections = re.split(r"#+\s*|^\d+\.\s+", analysis, flags=re.MULTILINE)
            sections = [s.strip() for s in sections if s.strip()]
            
            result = {
                "summary": sections[0] if len(sections) > 0 else "分析結果なし",
                "issues": self._extract_list_items(sections[1]) if len(sections) > 1 else [],
                "suggestions": self._extract_list_items(sections[2]) if len(sections) > 2 else []
            }
            
            return result
            
        except Exception as e:
            logger.error(f"コード品質分析エラー: {str(e)}")
            return {"error": f"分析エラー: {str(e)}"}
    
    def _get_language_from_extension(self, ext: str) -> str:
        """ファイル拡張子から言語名を取得する"""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell",
            ".sql": "SQL",
            ".md": "Markdown",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML"
        }
        return ext_map.get(ext, "プログラミング")
    
    def suggest_feature_implementation(self, repo_path: str, feature_description: str, target_file: str = None) -> Dict[str, Any]:
        """
        新機能の実装案を提案
        
        Args:
            repo_path: Gitリポジトリのパス
            feature_description: 実装する機能の説明
            target_file: 対象ファイル（オプション）
            
        Returns:
            実装案の辞書
        """
        if not self.use_openai:
            return {
                "summary": "OpenAI APIが無効なため、機能実装の提案は実行できません。",
                "code": None
            }
        
        logger.info(f"機能 '{feature_description}' の実装案を生成中...")
        
        try:
            # リポジトリの構造を把握
            structure_result = self._run_git_command(['git', 'ls-files'], cwd=repo_path)
            repo_files = structure_result.stdout.strip().split('\n')
            
            # 主要な言語を推測
            extensions = [os.path.splitext(f)[1] for f in repo_files if os.path.splitext(f)[1]]
            main_language = self._guess_main_language(extensions)
            
            existing_code = ""
            if target_file and os.path.exists(os.path.join(repo_path, target_file)):
                # 既存ファイルを読み込む
                try:
                    with open(os.path.join(repo_path, target_file), 'r', encoding='utf-8', errors='replace') as f:
                        existing_code = f.read()
                except Exception as e:
                    logger.warning(f"ファイル {target_file} の読み込み中にエラー: {str(e)}")
                    existing_code = f"# ファイル読み込みエラー: {str(e)}"
                
                messages = [
                    {"role": "system", "content": f"あなたは{main_language}の熟練プログラマーです。新機能の実装方法を提案してください。"},
                    {"role": "user", "content": f"以下の{main_language}コードに、「{feature_description}」という新機能を追加したいです。\n\n"
                                              f"既存コード（{target_file}）:\n```\n{existing_code}\n```\n\n"
                                              f"このコードを拡張して、上記の機能を実装する方法を提案してください。完全なコードを提供してください。"}
                ]
            else:
                # 新規ファイルの作成
                if not target_file:
                    # ファイル名を推測
                    target_file = self._suggest_filename(feature_description, main_language)
                
                messages = [
                    {"role": "system", "content": f"あなたは{main_language}の熟練プログラマーです。新機能を実装するためのコードを提供してください。"},
                    {"role": "user", "content": f"「{feature_description}」という機能を実装する{main_language}コードを作成してください。\n\n"
                                              f"以下のファイル名で実装します: {target_file}\n\n"
                                              f"完全なコードを提供してください。"}
                ]
            
            implementation = self._call_openai_api(messages)
            
            # コードブロック抽出
            code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", implementation, re.DOTALL)
            code = code_blocks[0] if code_blocks else implementation
            
            # コード以外の説明部分を抽出
            explanation = re.sub(r"```.*?```", "", implementation, flags=re.DOTALL).strip()
            
            result = {
                "target_file": target_file,
                "code": code,
                "explanation": explanation
            }
            
            return result
            
        except Exception as e:
            logger.error(f"機能実装提案エラー: {str(e)}")
            return {"error": f"実装提案エラー: {str(e)}"}
    
    def _guess_main_language(self, extensions: List[str]) -> str:
        """リポジトリの主要言語を推測"""
        if not extensions:
            return "Python"  # デフォルト
        
        # 拡張子の出現回数をカウント
        ext_count = {}
        for ext in extensions:
            ext = ext.lower()
            if ext in ext_count:
                ext_count[ext] += 1
            else:
                ext_count[ext] = 1
        
        # 最も多い拡張子
        most_common_ext = max(ext_count.items(), key=lambda x: x[1])[0]
        return self._get_language_from_extension(most_common_ext)
    
    def _suggest_filename(self, feature_description: str, language: str) -> str:
        """機能説明からファイル名を推測"""
        # 拡張子マッピング
        lang_to_ext = {
            "Python": ".py",
            "JavaScript": ".js",
            "TypeScript": ".ts",
            "Java": ".java",
            "C++": ".cpp",
            "C#": ".cs",
            "Ruby": ".rb",
            "Go": ".go",
            "Rust": ".rs",
            "PHP": ".php"
        }
        
        # スネークケースに変換
        name = feature_description.lower()
        name = re.sub(r'[^\w\s]', '', name)  # 特殊文字除去
        name = re.sub(r'\s+', '_', name)     # スペースをアンダースコアに
        
        # 長すぎる場合は短縮
        if len(name) > 30:
            words = name.split('_')
            if len(words) > 3:
                name = '_'.join(words[:3])
        
        # 拡張子を追加
        ext = lang_to_ext.get(language, ".txt")
        return name + ext
    
    def check_sensitive_info(self, repo_path: str) -> Dict[str, Any]:
        """
        変更内容から機密情報の漏洩をチェック
        
        Args:
            repo_path: Gitリポジトリのパス
            
        Returns:
            チェック結果の辞書
        """
        logger.info("変更内容から機密情報の漏洩をチェック中...")
        
        try:
            # git diffの実行（未コミットの変更とコミット済みでまだpushされていない変更）
            diff_staged = self._run_git_command(['git', 'diff', '--staged'], cwd=repo_path).stdout.strip()
            diff_commit = self._run_git_command(['git', 'diff', 'origin/main...HEAD'], cwd=repo_path).stdout.strip()
            
            # 何も変更がない場合は早期リターン
            if not diff_staged and not diff_commit:
                return {
                    "safe": True,
                    "message": "プッシュする変更はありません。",
                    "issues": []
                }
            
            # 変更ファイル一覧を取得
            files_to_push = self._run_git_command(
                ['git', 'diff', '--name-only', 'origin/main...HEAD'], cwd=repo_path
            ).stdout.strip().split('\n')
            
            # 正規表現パターンで機密情報をチェック
            patterns = {
                "APIキー": [
                    r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{16,})["\']\s*',
                    r'api[_-]?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{16,})["\']\s*',
                    r'access[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{16,})["\']\s*',
                    r'OPENAI_API_KEY["\']?\s*[:=]\s*["\']?([a-zA-Z0-9-]{20,})["\']\s*',
                    r'sk-[a-zA-Z0-9]{48}'  # OpenAI APIキーの形式
                ],
                "パスワード": [
                    r'password["\']?\s*[:=]\s*["\']?([^\'"\s]{3,})["\']\s*',
                    r'passwd["\']?\s*[:=]\s*["\']?([^\'"\s]{3,})["\']\s*',
                    r'pwd["\']?\s*[:=]\s*["\']?([^\'"\s]{3,})["\']\s*'
                ],
                "認証情報": [
                    r'bearer\s+[a-zA-Z0-9_-]{10,}',
                    r'authorization["\']?\s*[:=]\s*["\']?bearer\s+([a-zA-Z0-9_-]{10,})["\']\s*',
                    r'auth[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{10,})["\']\s*'
                ],
                "秘密鍵": [
                    r'-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)\s+PRIVATE\s+KEY-----',
                    r'private[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+]{10,})["\']\s*'
                ],
                "証明書": [
                    r'-----BEGIN\s+CERTIFICATE-----'
                ],
                "個人識別情報": [
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', # メールアドレス
                    r'\b\d{3}-\d{2}-\d{4}\b',  # 米国社会保障番号の形式
                    r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # クレジットカード番号の一般的な形式
                ]
            }
            
            # OpenAI APIを使用してさらに詳細なチェック
            if self.use_openai and (len(diff_staged) + len(diff_commit) < 4000):
                combined_diff = diff_staged + "\n" + diff_commit
                
                messages = [
                    {"role": "system", "content": "あなたはセキュリティ専門家です。コード内の機密情報を特定してください。"},
                    {"role": "user", "content": f"以下のgit diffの出力をチェックして、APIキー、パスワード、認証トークン、秘密鍵、証明書、個人情報などの"
                                              f"漏洩してはいけない機密情報が含まれていないか確認してください。問題が見つかった場合は、どの行に何の情報が"
                                              f"含まれているかを具体的に指摘してください。\n\n"
                                              f"{combined_diff}"}
                ]
                
                ai_analysis = self._call_openai_api(messages)
                
                # 問題があるかどうかを判断
                ai_found_issues = not any(phrase in ai_analysis.lower() for phrase in 
                                         ["機密情報は見つかりませんでした", "問題は検出されませんでした", "機密データは含まれていません"])
            else:
                ai_analysis = "差分が大きすぎるため、AIによる分析は実行されませんでした。"
                ai_found_issues = False
            
            # 正規表現による問題検出
            issues = []
            
            for file_path in files_to_push:
                if not file_path:  # 空の行をスキップ
                    continue
                    
                file_path = file_path.strip()
                abs_file_path = os.path.join(repo_path, file_path)
                
                if not os.path.exists(abs_file_path):
                    continue
                
                try:
                    with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        
                    for issue_type, patterns_list in patterns.items():
                        for pattern in patterns_list:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                context = content.splitlines()[line_num - 1]
                                issues.append({
                                    "file": file_path,
                                    "line": line_num,
                                    "type": issue_type,
                                    "context": context
                                })
                except Exception as e:
                    logger.warning(f"ファイル {file_path} の読み込み中にエラー: {str(e)}")
            
            # 結果を返す
            result = {
                "safe": len(issues) == 0 and not ai_found_issues,
                "issues": issues,
                "ai_analysis": ai_analysis if self.use_openai else "OpenAI APIが無効なため、AIによる分析は実行されませんでした。"
            }
            
            if not result["safe"]:
                if issues:
                    result["message"] = f"{len(issues)}件の機密情報の漏洩リスクが検出されました。"
                else:
                    result["message"] = "AIによる分析で機密情報の漏洩リスクが検出されました。"
            else:
                result["message"] = "機密情報の漏洩リスクは検出されませんでした。"
            
            return result
            
        except Exception as e:
            logger.error(f"機密情報チェックエラー: {str(e)}")
            return {
                "safe": False,
                "message": f"機密情報のチェック中にエラーが発生しました: {str(e)}",
                "issues": []
            }
    
    def execute_ai_git_command(self, command: str, repo_path: str, **kwargs) -> Dict[str, Any]:
        """
        AIを使用したGitコマンドを実行する
        
        Args:
            command: 実行するコマンド
            repo_path: Gitリポジトリのパス
            **kwargs: その他のパラメータ
            
        Returns:
            実行結果の辞書
        """
        if command == "ai-commit":
            # 変更があるか確認
            status_result = self._run_git_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout.strip():
                return {"success": False, "message": "コミットする変更がありません。"}
            
            # 変更をステージングエリアに追加
            self._run_git_command(['git', 'add', '--all'], cwd=repo_path)
            
            # コミットメッセージを生成
            commit_message = self.generate_commit_message(repo_path)
            
            # コミット実行
            try:
                self._run_git_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
                return {"success": True, "message": f"コミット成功: {commit_message}"}
            except Exception as e:
                return {"success": False, "message": f"コミットエラー: {str(e)}"}
                
        elif command == "ai-full-push":
            # 変更があるか確認
            status_result = self._run_git_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout.strip():
                return {"success": False, "message": "プッシュする変更がありません。"}
            
            # 現在のブランチ名を取得
            branch_result = self._run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path)
            current_branch = branch_result.stdout.strip()
            
            # 変更をステージングエリアに追加
            self._run_git_command(['git', 'add', '--all'], cwd=repo_path)
            
            # コミットメッセージをAIで生成
            commit_message = self.generate_commit_message(repo_path)
            
            # コミット実行
            try:
                commit_result = self._run_git_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            except Exception as e:
                return {"success": False, "message": f"コミットエラー: {str(e)}"}
            
            # ブランチ戦略のヒントを生成
            branch_strategy_hint = self._generate_branch_strategy_hint(repo_path, current_branch)
            
            # プッシュ実行
            target_branch = kwargs.get("branch", current_branch)
            try:
                push_result = self._run_git_command(['git', 'push', 'origin', target_branch], cwd=repo_path)
                return {
                    "success": True, 
                    "message": f"AI生成メッセージでコミットし、プッシュしました: {commit_message}",
                    "branch_hint": branch_strategy_hint
                }
            except Exception as e:
                return {"success": False, "message": f"プッシュエラー: {str(e)}"}
            
        elif command == "analyze-pr":
            pr_url = kwargs.get("pr_url", "")
            if not pr_url:
                return {"success": False, "message": "PR URLが指定されていません。"}
            
            result = self.analyze_pull_request(pr_url)
            if "error" in result:
                return {"success": False, "message": result["error"]}
            
            return {"success": True, "result": result}
            
        elif command == "analyze-code":
            file_path = kwargs.get("file_path", "")
            if not file_path:
                return {"success": False, "message": "ファイルパスが指定されていません。"}
            
            if not os.path.isabs(file_path):
                file_path = os.path.join(repo_path, file_path)
            
            result = self.analyze_code_quality(file_path)
            if "error" in result:
                return {"success": False, "message": result["error"]}
            
            return {"success": True, "result": result}
            
        elif command == "suggest-implementation":
            feature = kwargs.get("feature", "")
            if not feature:
                return {"success": False, "message": "機能の説明が指定されていません。"}
            
            target_file = kwargs.get("target_file", None)
            
            result = self.suggest_feature_implementation(repo_path, feature, target_file)
            if "error" in result:
                return {"success": False, "message": result["error"]}
            
            return {"success": True, "result": result}
            
        elif command == "check-sensitive-info":
            result = self.check_sensitive_info(repo_path)
            return {"success": True, "result": result}
            
        else:
            return {"success": False, "message": f"不明なコマンド: {command}"}
    
    def _generate_branch_strategy_hint(self, repo_path: str, current_branch: str) -> str:
        """
        現在のブランチとコミット履歴からブランチ戦略についてのヒントを生成
        
        Args:
            repo_path: リポジトリのパス
            current_branch: 現在のブランチ名
            
        Returns:
            ブランチ戦略のヒント
        """
        if not self.use_openai:
            return "ブランチ戦略ヒント: OpenAI APIが無効なため、ヒントは生成できません。"
        
        try:
            # ブランチ一覧の取得
            branches_result = self._run_git_command(['git', 'branch', '-a'], cwd=repo_path)
            branches = branches_result.stdout.strip()
            
            # コミット履歴の取得
            log_result = self._run_git_command(['git', 'log', '--oneline', '-n', '10'], cwd=repo_path)
            commit_history = log_result.stdout.strip()
            
            # リポジトリの構造情報
            # wc -l コマンドをパイプで繋げる代わりに、結果を取得してPythonで処理
            files_result = self._run_git_command(['git', 'ls-files'], cwd=repo_path)
            file_count = len(files_result.stdout.strip().split('\n'))
            
            # OpenAI APIでブランチ戦略ヒントを生成
            messages = [
                {"role": "system", "content": "あなたはGitブランチ戦略と開発ワークフローの専門家です。リポジトリの状態を分析し、最適なブランチ戦略を提案してください。"},
                {"role": "user", "content": f"""
                以下のGitリポジトリ情報から、適切なブランチ戦略についてのヒントを提供してください。
                現在のブランチ: {current_branch}
                
                ブランチ一覧:
                {branches}
                
                最近のコミット履歴:
                {commit_history}
                
                リポジトリの規模: 約{file_count}ファイル
                
                考慮すべきこと:
                1. チーム開発に適した戦略か
                2. feature/bugfix/releaseなどの命名規則
                3. マージ戦略の最適化
                4. この規模のプロジェクトに最適なワークフロー
                
                簡潔に3-5行程度でアドバイスをください。
                """}
            ]
            
            hint = self._call_openai_api(messages, max_tokens=150)
            return f"ブランチ戦略ヒント: {hint.strip()}"
            
        except Exception as e:
            logger.error(f"ブランチ戦略ヒント生成エラー: {str(e)}")
            return f"ブランチ戦略ヒント: 生成中にエラーが発生しました ({str(e)})"


# スクリプトとして直接実行された場合のエントリーポイント
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OpenAI APIを使用したGit操作支援ツール')
    parser.add_argument('command', choices=['ai-commit', 'ai-full-push', 'analyze-pr', 'analyze-code', 'suggest-implementation', 'check-sensitive-info'],
                        help='実行するコマンド')
    parser.add_argument('--repo', default='.', help='対象リポジトリのパス')
    parser.add_argument('--pr-url', help='分析するPR URL')
    parser.add_argument('--file', help='分析対象のファイルパス')
    parser.add_argument('--feature', help='実装する機能の説明')
    parser.add_argument('--target-file', help='機能を実装するターゲットファイル名')
    parser.add_argument('--branch', help='プッシュ先のブランチ')
    
    args = parser.parse_args()
    
    helper = OpenAIGitHelper()
    
    if args.command == 'ai-commit':
        result = helper.execute_ai_git_command('ai-commit', args.repo)
        
    elif args.command == 'ai-full-push':
        result = helper.execute_ai_git_command('ai-full-push', args.repo, branch=args.branch)
        
    elif args.command == 'analyze-pr':
        if not args.pr_url:
            print("エラー: PR URLが必要です。--pr-url オプションを使用してください。")
            sys.exit(1)
        result = helper.execute_ai_git_command('analyze-pr', args.repo, pr_url=args.pr_url)
        
    elif args.command == 'analyze-code':
        if not args.file:
            print("エラー: ファイルパスが必要です。--file オプションを使用してください。")
            sys.exit(1)
        result = helper.execute_ai_git_command('analyze-code', args.repo, file_path=args.file)
        
    elif args.command == 'suggest-implementation':
        if not args.feature:
            print("エラー: 機能の説明が必要です。--feature オプションを使用してください。")
            sys.exit(1)
        result = helper.execute_ai_git_command('suggest-implementation', args.repo, 
                                              feature=args.feature, target_file=args.target_file)
        
    elif args.command == 'check-sensitive-info':
        result = helper.execute_ai_git_command('check-sensitive-info', args.repo)
    
    if result["success"]:
        if args.command == 'ai-commit':
            print(f"成功: {result['message']}")
        else:
            print(json.dumps(result["result"], indent=2, ensure_ascii=False))
        sys.exit(0)
    else:
        print(f"エラー: {result['message']}")
        sys.exit(1) 