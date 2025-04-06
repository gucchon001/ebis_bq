"""
汎用ブラウザ操作モジュール

他のプロジェクトでも再利用可能な形式で設計された
Seleniumを使用したブラウザ自動化ユーティリティを提供します。
"""

# 修正: src.modules.generic.browser を src.modules.selenium.browser に変更
try:
    from src.modules.selenium.browser import Browser
except ImportError:
    # 一時的にブラウザ機能がないことを示す
    class BrowserNotImplemented:
        def __init__(self):
            raise NotImplementedError("Browser class is not implemented yet. Browser module is missing.")

    # 仮の対策として、エラーになるクラスを提供
    Browser = BrowserNotImplemented

__all__ = ['Browser'] 