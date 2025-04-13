# セレクタ更新レポート

## 更新内容
詳細分析ページの要素について、最新の状態で要素検出とセレクタ情報の更新を行いました。

## 更新したファイル
- `selectors_analysis.csv`
- `selectors_analysis.json`

## 主な変更点

### 「全トラフィック」タブの安定したセレクタ
「全トラフィック」タブの検出に成功し、複数の信頼性の高いセレクタを取得しました：

```
detailed_analysis,clickable_5,#navbar > nav > a:nth-child(2) > div,全トラフィック,サイドバー
```

### 日付範囲のセレクタ
日付範囲のセレクタ情報を更新しました。新しいセレクタは以下の通りです：

```
detailed_analysis,date_picker_trigger,.date-range-picker-container,期間選択,ナビゲーションバー
detailed_analysis,apply_button,button.applyBtn,適用,ボタン
detailed_analysis,date_input,.date-range-picker-container input[type='text'],,フォーム
```

### CSVダウンロードボタンのセレクタ
CSVダウンロードボタンのセレクタ情報を更新しました：

```
detailed_analysis,csv_download_button,button.csv-download,CSVダウンロード,ボタン
```

### その他のタブセレクタ
各種タブ要素のセレクタ情報を更新しました：

```
detailed_analysis,media_tab,a[data-rb-event-key='media'] > div,メディア,サイドバー
detailed_analysis,keyword_tab,a[data-rb-event-key='keyword'] > div,キーワード,サイドバー
detailed_analysis,ad_tab,a[data-rb-event-key='ad'] > div,広告,サイドバー
detailed_analysis,listing_tab,a[data-rb-event-key='listing'] > div,リスティング,サイドバー
```

## 更新日時
2025年04月13日 17:51
