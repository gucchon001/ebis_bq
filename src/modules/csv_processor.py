"""
CSVファイル処理モジュール

このモジュールは、CSVファイルの読み込みと解析を行い、スキーマ情報をJSON形式で出力する機能を提供します。
設定ファイル (settings.ini) から各種パラメータを取得して動作します。

機能:
- CSVファイルの読み込み (cp932/utf-8エンコーディング対応)
- 最初の10行を使用した効率的な文字コード判定
- ヘッダー行の取得と最初の5行のデータのログ表示
- データ型の推論とデータ整合性チェック
- スキーマ情報のJSON出力

使用方法:
$ python -m src.modules.csv_processor [CSVファイルパス] [オプション]

オプション:
--encoding ENCODING: エンコーディングを指定 (例: cp932, utf-8)
--header-row N: ヘッダー行の位置を指定 (デフォルト: 1)
"""

import os
import csv
import json
import chardet
import pandas as pd
import argparse  # 引数解析用
import sys  # システム終了用
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Set
from datetime import datetime
import re

from src.utils.environment import env
from src.utils.logging_config import get_logger

# ロガーの取得
logger = get_logger(__name__)

class CSVProcessor:
    """CSVファイル処理クラス"""
    
    # データ型の定義
    DATA_TYPES = {
        'STR': 'STR',
        'INT': 'INT',
        'FLOAT': 'FLOAT',  # 浮動小数点型を追加
        'DATE': 'DATE',
        'TIMESTAMP': 'TIMESTAMP',
        'BOOLEAN': 'BOOLEAN'
    }
    
    def __init__(self) -> None:
        """CSVProcessorクラスのコンストラクタ"""
        # 設定情報の取得
        self.csv_path = env.get_config_value('CSV_FILES', 'CSV_PATH', 'data/csv/')
        self.default_encoding = env.get_config_value('CSV_FILES', 'DEFAULT_ENCODING', 'cp932')
        self.header_row = int(env.get_config_value('CSV_FILES', 'HEADER_ROW', 1))
        self.schema_dir = env.get_config_value('CSV_FILES', 'SCHEMA_DIR', 'data/csv/schema/')
        
        # 新しく追加した設定値：デフォルトで処理するCSVファイル
        self.default_csv_file = env.get_config_value('CSV_FILES', 'DEFAULT_CSV_FILE', '')
        
        # 各パスをプロジェクトルートからの絶対パスに変換
        self.root_dir = env.get_project_root()
        self.csv_path = self.root_dir / self.csv_path
        self.schema_dir = self.root_dir / self.schema_dir
        
        # 必要なディレクトリの作成
        self._create_directories()
        
    def _create_directories(self) -> None:
        """必要なディレクトリを作成する"""
        for directory in [self.csv_path, self.schema_dir]:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"ディレクトリを作成しました: {directory}")
                
    def get_csv_path(self, filename: str, is_variable: bool = False) -> Path:
        """
        CSVファイルのパスを取得する
        
        Args:
            filename (str): ファイル名
            is_variable (bool): 可変ファイルかどうか（Trueの場合は可変ファイルディレクトリを使用）
            
        Returns:
            Path: CSVファイルのパス
        """
        return self.csv_path / filename
    
    def detect_encoding(self, file_path: Path, max_lines: int = 10) -> str:
        """
        ファイルのエンコーディングを検出する（最初の指定行数のみを使用）
        
        Args:
            file_path (Path): ファイルパス
            max_lines (int): 検出に使用する最大行数
            
        Returns:
            str: 検出されたエンコーディング
        """
        try:
            # 最初のmax_lines行だけ読み込む
            with open(file_path, 'rb') as f:
                sample_data = b''
                for _ in range(max_lines):
                    line = f.readline()
                    if not line:
                        break
                    sample_data += line
                
                if not sample_data:
                    logger.warning(f"ファイル {file_path} は空です。")
                    return self.default_encoding
                
                # 文字コード判定
                result = chardet.detect(sample_data)
                encoding = result['encoding']
                confidence = result.get('confidence', 0)
                
                logger.info(f"ファイル {file_path} のエンコーディング検出結果: {encoding} (確度: {confidence:.2f})")
                
                # 確度が低い場合はデフォルトエンコーディングを使用
                if confidence < 0.7:
                    logger.warning(f"エンコーディング検出の確度が低いため ({confidence:.2f})、デフォルトの {self.default_encoding} を使用します。")
                    return self.default_encoding
                
                return encoding
        except Exception as e:
            logger.error(f"エンコーディング検出中にエラーが発生しました: {str(e)}")
            return self.default_encoding
            
    def read_csv_file(self, file_path: Union[str, Path], encoding: Optional[str] = None) -> Tuple[List[str], List[List[str]], int]:
        """
        CSVファイルを読み込む
        
        Args:
            file_path (Union[str, Path]): ファイルパス
            encoding (Optional[str]): エンコーディング (指定がない場合は自動検出)
            
        Returns:
            Tuple[List[str], List[List[str]], int]: (ヘッダー行, データ行のリスト, レコード数)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
        if not encoding:
            encoding = self.detect_encoding(file_path)
            # 検出できなかった場合はデフォルトエンコーディングを使用
            if encoding is None:
                logger.warning(f"エンコーディングを検出できませんでした。デフォルトの {self.default_encoding} を使用します。")
                encoding = self.default_encoding
            
        try:
            logger.info(f"CSVファイル {file_path} を {encoding} エンコーディングで読み込みます。ヘッダー行: {self.header_row}")
            
            # pandasを使用してCSVファイルを読み込む
            df = pd.read_csv(file_path, encoding=encoding, header=self.header_row-1)
            
            # ヘッダー行とデータ行を取得
            headers = df.columns.tolist()
            data = df.values.tolist()
            record_count = len(data)
            
            logger.info(f"CSVファイル {file_path} を読み込みました。レコード数: {record_count}")
            
            # ヘッダー情報をログに出力
            logger.info(f"ヘッダー: {headers}")
            
            # 最初の5行をログに出力（データがある場合のみ）
            if data:
                max_preview_rows = min(5, len(data))
                logger.info(f"最初の {max_preview_rows} 行のデータ:")
                for i, row in enumerate(data[:max_preview_rows]):
                    logger.info(f"行 {i+1}: {row}")
            
            return headers, data, record_count
            
        except UnicodeDecodeError:
            # エンコーディングエラーが発生した場合、別のエンコーディングを試す
            alt_encoding = 'utf-8' if encoding and encoding.lower() == 'cp932' else 'cp932'
            logger.warning(f"エンコーディング {encoding} でエラーが発生しました。{alt_encoding} で再試行します。")
            return self.read_csv_file(file_path, alt_encoding)
            
        except Exception as e:
            logger.error(f"CSVファイル読み込み中にエラーが発生しました: {str(e)}")
            raise
    
    def infer_data_type(self, value: Any) -> str:
        """
        データ値からデータ型を推論する
        
        Args:
            value (Any): 推論対象の値
            
        Returns:
            str: 推論されたデータ型
        """
        if value is None or pd.isna(value) or value == '':
            return self.DATA_TYPES['STR']
            
        # 文字列に変換
        str_value = str(value).strip()
        
        # BOOLEAN型の判定
        if str_value.lower() in ['true', 'false', '0', '1', 'yes', 'no']:
            return self.DATA_TYPES['BOOLEAN']
            
        # FLOAT型の判定（小数点を含む数値）
        # 複雑な正規表現チェックではなく、直接変換を試みる方法に修正
        try:
            # カンマが含まれる場合は除去してから変換
            cleaned_value = str_value.replace(',', '')
            float_value = float(cleaned_value)
            
            # 整数値として表現できる場合はINT型
            if float_value.is_integer() and '.' not in str_value:
                return self.DATA_TYPES['INT']
            else:
                return self.DATA_TYPES['FLOAT']
        except ValueError:
            pass  # 数値変換に失敗した場合は次の判定へ
            
        # INT型の判定 - 上記のFLOAT判定でカバーされるため、単純化
        if re.match(r'^-?\d+$', str_value):
            return self.DATA_TYPES['INT']
            
        # DATE型の判定（YYYY/MM/DD, YYYY-MM-DD）
        if re.match(r'^\d{4}[/-]\d{1,2}[/-]\d{1,2}$', str_value):
            return self.DATA_TYPES['DATE']
            
        # TIMESTAMP型の判定（日付+時間）
        if re.match(r'^\d{4}[/-]\d{1,2}[/-]\d{1,2}[T\s]\d{1,2}:\d{1,2}(:\d{1,2})?', str_value):
            return self.DATA_TYPES['TIMESTAMP']
            
        # それ以外はSTR型
        return self.DATA_TYPES['STR']
    
    def check_data_type_consistency(self, column_name: str, data_type: str, values: List[Any]) -> Dict[str, Any]:
        """
        列のデータ型の整合性をチェックする
        
        Args:
            column_name (str): 列名
            data_type (str): 推論された主要データ型
            values (List[Any]): 列の値リスト
            
        Returns:
            Dict[str, Any]: 整合性チェック結果
        """
        inconsistent_values = []
        inconsistent_rows = []
        inconsistent_count = 0
        
        for idx, value in enumerate(values):
            if value is None or pd.isna(value) or value == '':
                continue  # 空値はスキップ
                
            # 現在の値から型を推測
            current_type = self.infer_data_type(value)
            
            # 主要データ型と異なる場合
            if current_type != data_type:
                inconsistent_count += 1
                # 全ての不整合値を記録
                inconsistent_values.append(value)
                inconsistent_rows.append(idx + 1)  # 1ベースの行番号
        
        consistency_rate = 1.0 - (inconsistent_count / len(values)) if values else 1.0
        
        # 整合性の結果を返す
        return {
            'column_name': column_name,
            'data_type': data_type,
            'consistency_rate': consistency_rate,
            'inconsistent_count': inconsistent_count,
            'inconsistent_values': inconsistent_values,
            'inconsistent_rows': inconsistent_rows
        }
    
    def generate_schema(self, headers: List[str], data: List[List[Any]]) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        ヘッダーとデータからスキーマを生成し、データ型の整合性もチェックする
        
        Args:
            headers (List[str]): ヘッダー行
            data (List[List[Any]]): データ行
            
        Returns:
            Tuple[List[Dict[str, str]], List[Dict[str, Any]]]: (スキーマ情報、整合性チェック結果)
        """
        schema = []
        consistency_results = []
        
        for idx, column_name in enumerate(headers):
            # データがない場合はSTR型とする
            if not data or idx >= len(data[0]):
                data_type = self.DATA_TYPES['STR']
                sample_data = ""
                consistency_check = {
                    'column_name': column_name,
                    'data_type': data_type,
                    'consistency_rate': 1.0,
                    'inconsistent_count': 0,
                    'inconsistent_values': [],
                    'inconsistent_rows': []
                }
            else:
                # 列のすべての値を調査してデータ型を決定
                column_values = [row[idx] for row in data if idx < len(row)]
                
                # 最も多いデータ型を採用
                type_counts = {}
                for value in column_values:
                    inferred_type = self.infer_data_type(value)
                    type_counts[inferred_type] = type_counts.get(inferred_type, 0) + 1
                
                # データ型の決定（最も多いタイプ）
                if type_counts:
                    data_type = max(type_counts.items(), key=lambda x: x[1])[0]
                else:
                    data_type = self.DATA_TYPES['STR']
                
                # サンプルデータの取得（最新のレコードから空でないデータを検索）
                sample_data = ""
                # データは最新のものが先頭にあるので、先頭から検索
                for row in data:
                    if idx < len(row) and row[idx] is not None and pd.notna(row[idx]) and str(row[idx]).strip() != '':
                        sample_data = row[idx]
                        break
                
                # データ型の整合性チェック
                consistency_check = self.check_data_type_consistency(column_name, data_type, column_values)
            
            # スキーマ情報の作成
            schema.append({
                'COLUMN_ORIGIN_NAME': column_name,
                'DATA_TYPE': data_type,
                'COLUMN_AFTER_NAME': '',  # 将来の拡張用
                'DESCRIPTION': '',  # 将来の拡張用
                'SAMPLE_DATA': sample_data,  # サンプルデータを追加
                'CONSISTENCY_RATE': consistency_check['consistency_rate'],  # 整合性率
                'INCONSISTENT_COUNT': consistency_check['inconsistent_count'],  # 不整合件数
                'INCONSISTENT_SAMPLES': consistency_check['inconsistent_values'][:10] if consistency_check['inconsistent_values'] else []  # 不整合サンプル（最大10件）
            })
            
            # 整合性チェック結果を追加
            consistency_results.append(consistency_check)
            
            # 整合性が90%未満の場合は警告ログを出力
            if consistency_check['consistency_rate'] < 0.9:
                logger.warning(f"列 '{column_name}' のデータ型整合性が低いです ({consistency_check['consistency_rate']:.2%})。"
                            f"主要タイプ: {data_type}, 不整合値数: {consistency_check['inconsistent_count']}")
                # ログ出力用に不整合値の例を最大10件に制限
                log_inconsistent_values = consistency_check['inconsistent_values'][:10]
                log_inconsistent_rows = consistency_check['inconsistent_rows'][:10]
                if log_inconsistent_values:
                    logger.warning(f"不整合値の例 (表示は最大10件): {log_inconsistent_values}")
                    logger.warning(f"不整合の行番号 (表示は最大10件): {log_inconsistent_rows}")
            
        return schema, consistency_results
        
    def save_schema_to_json(self, schema: List[Dict[str, str]], consistency_results: List[Dict[str, Any]], csv_file_path: Union[str, Path]) -> Path:
        """
        スキーマと整合性チェック結果を一つのJSONファイルとして保存
        
        Args:
            schema (List[Dict[str, str]]): スキーマ情報
            consistency_results (List[Dict[str, Any]]): 整合性チェック結果
            csv_file_path (Union[str, Path]): CSVファイルのパス
            
        Returns:
            Path: 保存したJSONファイルのパス
        """
        csv_file_path = Path(csv_file_path)
        # 統合JSONのファイル名
        json_file_name = f"{csv_file_path.stem}_schema.json"
        json_path = self.schema_dir / json_file_name
        
        # 整合性チェック結果の非シリアライズ可能なオブジェクトを変換
        serializable_results = []
        for result in consistency_results:
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, (str, int, float, bool, list, dict, tuple)) or value is None:
                    serializable_result[key] = value
                else:
                    serializable_result[key] = str(value)
            serializable_results.append(serializable_result)
        
        # スキーマと整合性チェック結果を一つのオブジェクトにまとめる
        combined_data = {
            "schema": schema,
            "consistency_results": serializable_results
        }
            
        # 統合JSONファイルを保存
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"スキーマと整合性チェック結果を統合して保存しました: {json_path}")
        return json_path
        
    def process_csv_file(self, csv_path: Union[str, Path], encoding: Optional[str] = None) -> Dict[str, Any]:
        """
        CSVファイルを処理し、ヘッダー、データ、スキーマを取得
        
        Args:
            csv_path (Union[str, Path]): CSVファイルのパス
            encoding (Optional[str]): エンコーディング（指定なしの場合は自動検出）
            
        Returns:
            Dict[str, Any]: 処理結果（ヘッダー、データ、レコード数、スキーマ、スキーマファイルパス）
        """
        csv_path = Path(csv_path)
        
        # 処理開始ログ
        logger.info(f"CSVファイル {csv_path} の処理を開始します。")
        
        # CSVファイルの読み込み
        headers, data, record_count = self.read_csv_file(csv_path, encoding)
        
        # スキーマの生成と整合性チェック
        schema, consistency_results = self.generate_schema(headers, data)
        
        # スキーマと整合性チェック結果のJSON保存
        schema_path = self.save_schema_to_json(schema, consistency_results, csv_path)
        
        # 処理結果のサマリーをログに出力
        logger.info(f"CSVファイル {csv_path} の処理が完了しました。")
        logger.info(f"ヘッダー数: {len(headers)}, レコード数: {record_count}")
        
        # 整合性チェックの統計情報をログに出力
        if consistency_results:
            low_consistency_columns = [r['column_name'] for r in consistency_results if r['consistency_rate'] < 0.9]
            if low_consistency_columns:
                logger.warning(f"整合性が低い列が {len(low_consistency_columns)} 個あります: {', '.join(low_consistency_columns)}")
            else:
                logger.info("すべての列でデータ型の整合性が90%以上です。")
        
        return {
            'headers': headers,
            'data': data,
            'record_count': record_count,
            'schema': schema,
            'schema_path': schema_path,
            'consistency_results': consistency_results
        } 

# コマンドライン引数からの実行をサポートするためのメイン関数
def main():
    """
    コマンドラインからCSVProcessor機能を実行する
    
    使用例：
    python -m src.modules.csv_processor data.csv
    python -m src.modules.csv_processor mydata.csv --encoding utf-8
    python -m src.modules.csv_processor --use-default
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='CSVファイル処理ツール')
    
    # ファイル指定グループ
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument('csv_file', nargs='?', type=str, help='処理するCSVファイル名')
    file_group.add_argument('--use-default', action='store_true', help='settings.iniで指定されたデフォルトCSVファイルを使用')
    
    # その他のオプション
    parser.add_argument('--encoding', type=str, help='CSVファイルのエンコーディングを指定')
    parser.add_argument('--header-row', type=int, help='ヘッダー行の位置を指定（デフォルト: 1）')
    
    # 引数の解析
    args = parser.parse_args()
    
    # 環境変数のロード
    env.load_env()
    
    # CSVProcessorのインスタンス化
    processor = CSVProcessor()
    
    # ヘッダー行位置が指定されている場合、上書き
    if args.header_row:
        processor.header_row = args.header_row
    
    # ファイルパスの決定
    if args.csv_file:
        # ファイル名が直接指定された場合
        csv_filename = args.csv_file
        csv_path = processor.get_csv_path(csv_filename)
    elif args.use_default:
        # デフォルトCSVファイルを使用する場合
        if not processor.default_csv_file:
            logger.error("settings.iniにDEFAULT_CSV_FILEが設定されていません。")
            print("エラー: settings.iniにDEFAULT_CSV_FILEが設定されていません。")
            sys.exit(1)
        
        csv_filename = processor.default_csv_file
        csv_path = processor.get_csv_path(csv_filename)
    else:
        # どちらも指定されていない場合、エラー
        parser.print_help()
        sys.exit(1)
    
    # ファイルの存在確認
    if not csv_path.exists():
        logger.error(f"ファイルが見つかりません: {csv_path}")
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)
    
    try:
        # CSVファイルの処理
        logger.info(f"CSVファイル {csv_path} の処理を開始します。")
        result = processor.process_csv_file(csv_path, args.encoding)
        
        # 処理結果の表示
        print(f"\n--- CSVファイル処理結果 ---")
        print(f"ファイル: {csv_path}")
        print(f"エンコーディング: {args.encoding if args.encoding else '自動検出'}")
        print(f"ヘッダー行: {processor.header_row}")
        print(f"ヘッダー数: {len(result['headers'])}")
        print(f"レコード数: {result['record_count']}")
        print(f"スキーマファイル: {result['schema_path']}")
        
        # スキーマ情報の要約表示
        print("\nスキーマ情報:")
        column_types = {}
        for col in result['schema']:
            col_name = col['COLUMN_ORIGIN_NAME']
            data_type = col['DATA_TYPE']
            column_types[data_type] = column_types.get(data_type, 0) + 1
            print(f"  - {col_name}: {data_type}")
        
        # データ型の集計
        print("\nデータ型の集計:")
        for type_name, count in column_types.items():
            print(f"  - {type_name}: {count}列")
        
        # 整合性が低い列の警告表示
        low_consistency_columns = []
        for consistency in result.get('consistency_results', []):
            if consistency['consistency_rate'] < 0.9:
                low_consistency_columns.append({
                    'column': consistency['column_name'],
                    'rate': consistency['consistency_rate'],
                    'type': consistency['data_type']
                })
        
        if low_consistency_columns:
            print("\n警告: 以下の列でデータ型の整合性が低いです（90%未満）:")
            for col_info in low_consistency_columns:
                print(f"  - {col_info['column']}: {col_info['rate']:.2%} ({col_info['type']}型)")
        else:
            print("\nすべての列でデータ型の整合性が良好です（90%以上）。")
        
        print("\n処理が正常に完了しました。")
        logger.info(f"CSVファイル {csv_path} の処理が正常に完了しました。")
        
    except Exception as e:
        logger.error(f"CSVファイル処理中にエラーが発生しました: {e}", exc_info=True)
        print(f"エラー: {e}")
        sys.exit(1)

# スクリプトとして実行された場合
if __name__ == "__main__":
    main() 