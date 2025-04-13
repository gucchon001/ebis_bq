"""
HTMLセレクタ解析ツールの実行スクリプト

使用例:
$ python -m src.utils.html_selector_analyzer.execute https://example.com
"""

import os
import logging
import argparse
from src.utils.html_selector_analyzer.selector_analyzer import HTMLSelectorAnalyzer

# ロガー設定
logger = logging.getLogger(__name__)

def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='HTMLページからセレクタ要素を抽出するツール')
    parser.add_argument('url', help='解析するURL')
    parser.add_argument('--output-dir', '-o', help='出力ディレクトリ', default=os.path.join('data', 'page_analyze'))
    parser.add_argument('--headless', '-hl', action='store_true', help='ヘッドレスモードを使用する')
    parser.add_argument('--csv', '-c', help='CSVファイル名', default='selectors_analysis.csv')
    parser.add_argument('--json', '-j', help='JSONファイル名', default='selectors_analysis.json')
    parser.add_argument('--save-html', '-s', action='store_true', help='HTMLソースを保存する', default=True)
    args = parser.parse_args()
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 出力ディレクトリの作成
    os.makedirs(args.output_dir, exist_ok=True)
    
    # セレクタ解析ツールの初期化
    analyzer = HTMLSelectorAnalyzer(
        output_dir=args.output_dir,
        headless=args.headless,
        logger=logger
    )
    
    try:
        # ブラウザのセットアップ
        print(f"ブラウザをセットアップしています...")
        if not analyzer.setup():
            print("ブラウザのセットアップに失敗しました")
            return 1
        
        # URLに移動
        print(f"ページに移動しています: {args.url}")
        if not analyzer.navigate_to(args.url):
            print(f"ページ移動に失敗しました: {args.url}")
            return 1
        
        # ページ解析
        print("ページを解析しています...")
        result = analyzer.analyze_page(save_html=args.save_html)
        if not result["success"]:
            print("ページ解析に失敗しました")
            return 1
            
        if result["html_file"]:
            print(f"HTMLソースを保存しました: {result['html_file']}")
        
        # CSVファイルに出力
        print(f"CSVファイルに出力しています: {args.csv}")
        csv_path = analyzer.export_to_csv(args.csv)
        
        # JSONファイルに出力
        print(f"JSONファイルに出力しています: {args.json}")
        json_path = analyzer.export_to_json(args.json)
        
        if csv_path and json_path:
            print(f"\n処理が完了しました：")
            print(f"CSVファイル: {csv_path}")
            print(f"JSONファイル: {json_path}")
            print(f"セレクタ数: {len(analyzer.selectors)}件")
            return 0
        else:
            print("出力ファイルの作成に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"実行中にエラーが発生しました: {e}")
        print(f"エラーが発生しました: {e}")
        return 1
        
    finally:
        # ブラウザを閉じる
        print("ブラウザを終了しています...")
        analyzer.close()

if __name__ == "__main__":
    import sys
    sys.exit(main()) 