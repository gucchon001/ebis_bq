#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Slack通知機能

エラーやイベント発生時にSlackへ通知を送信するためのユーティリティクラスを提供します。
環境変数からWebhook URLを取得し、指定されたメッセージをSlackに送信します。
環境設定により、成功/失敗時の通知制御が可能です。
"""

import os
import json
import requests
from typing import Dict, Any, Optional, Union
import traceback
import platform
import socket
from datetime import datetime

from src.utils.logging_config import get_logger
from src.utils.environment import env

logger = get_logger(__name__)

class SlackNotifier:
    """
    Slack通知を送信するユーティリティクラス
    環境設定に基づいた通知制御が可能
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        SlackNotifierの初期化
        
        Args:
            webhook_url (Optional[str]): Slack Webhook URL。指定しない場合は環境に応じて自動選択
        """
        self.webhook_url = webhook_url
        self.current_env = env.get_environment()
        
        # 設定からの通知設定読み込み
        self.notify_success = env.get_config_value(self.current_env, "NOTIFY_SUCCESS", True)
        self.notify_error = env.get_config_value(self.current_env, "NOTIFY_ERROR", True)
        
        # Slack設定の読み込み
        self.footer_text = env.get_config_value("slack", "FOOTER_TEXT", "プロジェクト通知")
        self.icon_url = env.get_config_value("slack", "ICON_URL", 
                                            "https://platform.slack-edge.com/img/default_application_icon.png")
        self.default_color = env.get_config_value("slack", "DEFAULT_COLOR", "#36a64f")
        self.error_color = env.get_config_value("slack", "ERROR_COLOR", "#ff0000")
        self.success_color = env.get_config_value("slack", "SUCCESS_COLOR", "#2eb886")
        
        # Webhook URL取得
        if not self.webhook_url:
            self._load_webhook_url()
    
    def _load_webhook_url(self) -> None:
        """
        環境に応じたWebhook URLを読み込む
        開発環境と本番環境で異なるWebhook URLを使用
        """
        try:
            # 環境に応じたURLの環境変数名を設定
            env_var_name = "SLACK_WEBHOOK_PROD" if self.current_env == "production" else "SLACK_WEBHOOK_DEV"
            
            # 環境変数からURLを取得
            self.webhook_url = env.get_env_var(env_var_name)
            
            if self.webhook_url:
                logger.info(f"{self.current_env}環境用のWebhook URLを取得しました")
            else:
                # バックアップとして一般的な環境変数名も確認
                self.webhook_url = env.get_env_var("SLACK_WEBHOOK")
                if self.webhook_url:
                    logger.info("汎用Webhook URLを取得しました")
                else:
                    logger.warning(f"Webhook URL ({env_var_name})が設定されていません")
        
        except Exception as e:
            logger.error(f"Webhook URL取得中にエラーが発生しました: {str(e)}")
            self.webhook_url = None
    
    def should_notify(self, is_error: bool = False) -> bool:
        """
        現在の設定で通知すべきかを判断
        
        Args:
            is_error (bool): エラー通知の場合はTrue
            
        Returns:
            bool: 通知すべき場合はTrue
        """
        if is_error:
            return self.notify_error
        return self.notify_success
    
    def send_message(self, message: str, title: Optional[str] = None, 
                     color: Optional[str] = None, fields: Optional[Dict[str, str]] = None,
                     is_error: bool = False) -> bool:
        """
        Slackにメッセージを送信
        
        Args:
            message (str): 送信するメッセージ本文
            title (Optional[str]): メッセージのタイトル
            color (Optional[str]): メッセージの色 (指定なしの場合はデフォルト色)
            fields (Optional[Dict[str, str]]): 追加のフィールド情報
            is_error (bool): エラーメッセージかどうか
            
        Returns:
            bool: 送信が成功した場合はTrue、失敗した場合はFalse
        """
        # 通知設定に基づいて送信すべきか判断
        if not self.should_notify(is_error):
            logger.info(f"通知設定により、{'エラー' if is_error else '成功'}通知はスキップされました")
            return True
        
        if not self.webhook_url:
            logger.warning("Webhook URLが設定されていないため、Slackへの通知はスキップされました")
            return False
        
        # 色が指定されていない場合はデフォルト値を使用
        if color is None:
            color = self.error_color if is_error else self.default_color
            
        try:
            # 現在のホスト名とIPアドレスを取得
            hostname = platform.node()
            try:
                ip_address = socket.gethostbyname(socket.gethostname())
            except:
                ip_address = "不明"
                
            # 現在の日時を取得
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 基本的なフィールド情報を設定
            default_fields = [
                {
                    "title": "環境",
                    "value": self.current_env,
                    "short": True
                },
                {
                    "title": "ホスト",
                    "value": f"{hostname} ({ip_address})",
                    "short": True
                },
                {
                    "title": "発生時刻",
                    "value": current_time,
                    "short": True
                }
            ]
            
            # 追加のフィールド情報があれば追加
            if fields:
                for key, value in fields.items():
                    default_fields.append({
                        "title": key,
                        "value": value,
                        "short": True
                    })
            
            # Slackメッセージのペイロードを作成
            payload = {
                "attachments": [
                    {
                        "fallback": title or "通知",
                        "color": color,
                        "title": title or "通知",
                        "text": message,
                        "fields": default_fields,
                        "footer": self.footer_text,
                        "footer_icon": self.icon_url,
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # POSTリクエストを送信
            logger.info(f"Slack通知を送信しています: {title}")
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            
            # レスポンスをチェック
            if response.status_code == 200 and response.text == 'ok':
                logger.info(f"Slack通知が正常に送信されました: {title}")
                return True
            else:
                logger.error(f"Slack通知の送信に失敗しました: ステータスコード={response.status_code}, レスポンス={response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack通知の送信中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def send_error(self, error_message: str, exception: Optional[Exception] = None, 
                  title: str = "エラー発生", context: Optional[Dict[str, str]] = None) -> bool:
        """
        エラー情報をSlackに送信
        
        Args:
            error_message (str): エラーの説明メッセージ
            exception (Optional[Exception]): 発生した例外オブジェクト
            title (str): メッセージのタイトル (デフォルト: 'エラー発生')
            context (Optional[Dict[str, str]]): エラー発生時のコンテキスト情報
            
        Returns:
            bool: 送信が成功した場合はTrue、失敗した場合はFalse
        """
        # エラーメッセージを構築
        message = f"*{error_message}*\n"
        
        # 例外情報があれば追加
        if exception:
            message += f"\n```\n{str(exception)}\n```"
            
            # スタックトレースも追加
            stack_trace = traceback.format_exc()
            if stack_trace and stack_trace != "NoneType: None\n":
                message += f"\n*スタックトレース:*\n```\n{stack_trace[:1000]}```"
                if len(stack_trace) > 1000:
                    message += "\n(スタックトレースが長すぎるため省略されました)"
        
        # 追加のコンテキスト情報
        fields = {}
        if context:
            fields.update(context)
            
        # エラーメッセージを送信 (エラーフラグをTrue)
        return self.send_message(message, title, self.error_color, fields, is_error=True)
    
    def send_success(self, message: str, title: str = "処理完了", 
                     context: Optional[Dict[str, str]] = None) -> bool:
        """
        成功情報をSlackに送信
        
        Args:
            message (str): 成功メッセージ
            title (str): メッセージのタイトル (デフォルト: '処理完了')
            context (Optional[Dict[str, str]]): コンテキスト情報
            
        Returns:
            bool: 送信が成功した場合はTrue、失敗した場合はFalse
        """
        return self.send_message(message, title, self.success_color, context, is_error=False)
    
    @staticmethod
    def get_instance() -> 'SlackNotifier':
        """
        SlackNotifierのシングルトンインスタンスを取得
        
        Returns:
            SlackNotifier: SlackNotifierのインスタンス
        """
        return SlackNotifier() 