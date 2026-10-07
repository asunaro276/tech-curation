# Design

## Context

収集パイプラインは `plan → [github, rss] → merge_filter → fetch_content → select → summarize_format → review ⇄ revise` の順に動く。LLM 呼び出しはすべて `src/tech_curation/llm.py` の `chat()`（DeepSeek）を通る。

- `merge_filter` は記事ごとに DeepSeek に 0〜1 の数値を文字列で返させ、`float()` で読む。トピックの割り当ては正規表現によるキーワードマッチで行っている。
- `select` は全記事を1つのプロンプトにまとめ、残す記事のインデックスを JSON 配列で返させる。トピック別の本数はプロンプトに直書きしている。

Jev は1つの state（テキストまたは JSON）に対して名前付きの質問をまとめて評価し、`Noul`（yes/no の確率）、`Choice`（ラベルの選択と各ラベルの確率）、`Score`（段階評価の期待値と分布）のいずれかを返す。文章は生成せず、記事どうしを比べる機能もない。

## Goals / Non-Goals

**Goals:**
- 「1記事ずつの判定」を Jev に、「本数の制御」をコードに分ける。
- 判定基準を `prompts.md` に置き、自己改善ループの対象にする。

**Non-Goals:**
- 同じ話題の記事をまとめること（後続の `topic-grouping-dedup` で扱う）。
- 要約・コンテンツ種別判定・review / revise を Jev に移すこと（文章を生成するため DeepSeek のまま）。
- 重複除去のロジック（URL・タイトル・ランキングページ）を変えること。

## Decisions

### D1. Jev 呼び出しを `src/tech_curation/jev.py` に集約する
`llm.py` と同じ位置づけで、`TypeSafeClient` の生成、判定基準から質問を組み立てる処理、失敗時の中立値の返却をこのモジュールにまとめる。ノード側は「記事 → 判定結果の dict」だけを扱う。
- 代替案: 各ノードで SDK を直接呼ぶ。→ フォールバックとテスト用モックが散らばるため採らない。

### D2. Merge&Filter では1記事につき1回の呼び出しで関連度とトピックを判定する
```
state = {"title", "source", "body": body[:1500]}
questions = {
  "relevance": Score(criteria=<relevance_criteria の段階リスト>),
  "topic":     Choice(criteria={<アクティブなトピック>: <説明>, "トレンド": "どれにも当てはまらない"}),
}
```
- 関連度は `score / (段階数 - 1)` で 0〜1 に正規化し、既存の `_SOURCE_BOOST` と `filter_threshold` をそのまま適用する。
- RSS フィードのトピックヒントがある記事は、ヒントを優先する（現行の挙動と同じ）。
- 正規表現によるキーワードマッチ（`_assign_topic`）は、Jev の呼び出しが失敗したときのフォールバックとしてだけ残す。
- 代替案: トピック判定は正規表現のまま残す。→ 「rails」を含まない Rails 記事などを取りこぼすため、同じ呼び出しに質問を足すほうが得。出力は課金されないのでコストはほぼ変わらない。

### D3. Select は「Noul で判定 → トピック内で並べて上位 K 本」にする
```
worth = Noul(instructions=<worth_criteria>)   # state は本文 1500 文字まで
↓
トピックごとに worth の降順に並べる → 上位 K 本（K = topic_quotas[topic] または既定値）
```
- 最低1本の保証は K ≥ 1 によって自然に満たされる。
- 並列数は現行の `MAX_WORKERS = 12` に合わせる。

### D4. 設定の置き場所
`prompts.md` に3つのセクションを追加し、`AgentConfig` に読み込む。

```
## relevance_criteria        ← Score の段階（行ごとに 0, 1, 2, …）
- 0: 指定トピックと無関係
- 1: …
- 4: トピックの中心的な技術内容

## worth_criteria            ← Noul の instructions（自由文）

## topic_quotas              ← トピックごとの上限本数
- Go: 1
- Claude: 3
- トレンド: 5
- default: 2
```
- 既存の `select.py` に直書きされている本数（Go 1、TS/JS 1〜2、…）を、各トピックの上限値として初期値にする。
- `relevance_score_prompt` は読み込みは続けるが、どこからも使わない。セクションの削除は利用者に任せる。

### D5. 自己改善ループの変更対象を広げる
`generate_changes` / `revise_proposal` のシステムプロンプトに、`relevance_criteria`・`worth_criteria`（`prompt_changes`）と `topic_quotas.<topic>`（`param_changes`）を変更可能なキーとして追加する。`update_config` は `topic_quotas.<topic>` 形式のキーを `source_weights.<source>` と同じ方法で扱う。

## Risks / Trade-offs

- [日本語記事の判定精度が未知] → Zenn / Qiita が中心なので、導入前に過去のレポート記事 20〜30 本で DeepSeek の判定結果と比べ、大きくずれる場合は基準の文言を調整する。
- [入力長の上限が未確認] → 本文は 1500 文字で切る。上限が分かったら調整する。
- [Jev の障害でレポートが空になる] → すべての判定を中立値 0.5 にフォールバックし、本数制御だけでレポートを作る（spec の「Selection survives judgment failures」）。
- [`typesafe-sdk` が `httpx2` に依存し、既存の `httpx` と共存する] → コンテナのイメージサイズと import の衝突がないことをビルドで確認する。
- [段階評価の正規化によってスコアの分布が変わり、`filter_threshold=0.5` が合わなくなる] → 導入後のログでスコア分布を見て、閾値を手動か自己改善ループで調整する。

## Migration Plan

1. `typesafe-sdk` を追加し、収集 Lambda に `TYPESAFE_API_KEY` を設定する。
2. `prompts.md` に新しいセクションを追加する（未記載の場合はコード内の既定値で動く）。
3. デプロイ後、最初の数回はログで `[score]` と `[select]` の出力を確認する。
4. ロールバックは、以前のコンテナイメージを再デプロイするだけでよい。`prompts.md` に追加したセクションは旧コードでは無視される。

## Open Questions

- Jev の入力長の上限と、日本語に対する実際の判定精度（実装時に確認し、本文の切り出し長と基準の文言で調整する）。
- `topic_quotas` の既定値（`default`）を 2 とするか、`max_items_per_run` から計算するか。
