# Proposal

## Why

同じ出来事を扱う記事（公式リリースノート・Zenn の解説・Qiita のまとめなど）が別々の項目としてレポートに並び、前日以前に読んだ話題も再び載ることがある。今の重複除去は URL とタイトル先頭の一致しか見ておらず、話題レベルの重複は Select のプロンプト任せだった。`adopt-jev-selection` で Select が記事を1本ずつ判定する方式に変わり、記事どうしを比べる仕組みがなくなるため、話題単位でまとめる仕組みを明示的に用意する必要がある。

## What Changes

- 本文取得済みの候補記事を、トピックごとに worth の高い順に1本ずつ見て、既存のグループに入れるか新しいグループを作るかを判定モデル（Jev の Choice）で決める（貪欲法）。同じ出来事を扱う記事（例: リリースノートとその解説記事）は同じグループとする。
- 過去 `recency_days` 日分のレポートに載ったグループも選択肢に含める。過去と同じ話題なら落とし、続報（RC → 正式版など）なら残して前回のレポートへのリンクを付ける。
- グループの代表記事を「一次情報 > 日本語 > worth」の順で選ぶ。一次情報かどうかは worth と同じ呼び出しで判定し、日本語かどうかはコードで判定する。
- トピック別の上限本数を、記事数ではなくグループ数で数える。
- 要約をグループ単位で行う。代表記事と関連記事の内容を合わせた1本の要約を書き、全記事へのリンクを並べる。
- レポートと一緒に、その日に載せたグループの記録（`items.json`）を保存する。
- フィードバック欄に `dup=` を追加し、「今日の別の項目と同じ話題だった」「過去に読んだ」を記入できるようにする。自己改善ループはこれをもとにグループ判定の基準（`grouping_criteria`）を調整する。
- **BREAKING**: レポートの1セクションが「1記事」から「1グループ」になり、フィードバック欄の形式が変わる（旧形式も引き続きパースできる）。

## Capabilities

### New Capabilities
- `topic-grouping`: 候補記事を話題単位のグループにまとめ、過去のレポートとの重複と続報を判定し、代表記事を選ぶ振る舞い。

### Modified Capabilities
- `article-selection`: トピック別の上限本数を記事数ではなくグループ数に適用する（`adopt-jev-selection` で新設される capability）。
- `obsidian-output`: レポートのセクションをグループ単位にし、統合要約・関連記事リンク・続報リンク・`dup=` 欄を含める。日ごとのグループ記録を保存する。
- `feedback-capture`: フィードバックコメントの `dup=` を任意項目としてパースする。
- `self-improvement`: `dup=` フィードバックを分析に使い、`grouping_criteria` を変更できるようにする。

## Impact

- **前提**: `adopt-jev-selection` の実装・アーカイブが先に済んでいること（Select ノードと `jev.py` を拡張するため）
- **コード**: `collect/nodes/select.py`（グループ分け）、`collect/nodes/merge_filter.py`（候補枠の拡大）、`collect/nodes/summarize_format.py`・`review.py`・`revise.py`（グループ単位化）、`collect/state.py`、`obsidian/report.py`・`templates.py`、`feedback/parser.py`、`improve/nodes/*`、`handler_collect.py`
- **データ**: vault に `tech-curation/YYYY-MM-DD/items.json` が毎日追加される
- **設定**: `prompts.md` に `grouping_criteria` セクションを追加
- **コスト**: Jev 呼び出しが候補1本につき1回増える（トピック内は逐次実行のため、実行時間が数秒程度延びる）
