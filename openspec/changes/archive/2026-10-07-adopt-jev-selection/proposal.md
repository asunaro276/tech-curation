# Proposal

## Why

記事選定は DeepSeek に自由文で答えさせ、その文字列を `float()` や JSON 配列として解析している。そのため出力の揺れでパースが失敗したり、プロンプトに直書きしたトピック別本数が守られなかったりする。TypeSafe AI の Jev（System One モデル）は型付きの判定値だけを返し、高速・安価なので、「1記事ずつ判定する」部分を Jev に、「本数をそろえる」部分をコードに分けることで、選定を安定させ制御しやすくできる。

## What Changes

- Jev（`typesafe-sdk`）を呼び出す共通クライアントを追加する。API キーは `TYPESAFE_API_KEY` 環境変数から読む。
- Merge&Filter の関連度スコアリングを、DeepSeek の自由文出力から Jev の `Score`（段階評価）に置き換える。同じ呼び出しで、記事がどのトピックに属するかを `Choice` で判定する。RSS フィードのトピックヒントは引き続き優先する。
- Select ノードを置き換える。本文取得後に各記事を Jev の `Noul`（「要約する価値があるか」）で判定し、トピックごとに確率の高い順で上位 K 本をコードで残す。
- トピック別の残す本数をプロンプト直書きから `prompts.md` の設定（`topic_quotas`）に移す。
- Jev に渡す判定基準（instructions / criteria）を `prompts.md` の新しいセクション（`relevance_criteria`、`worth_criteria`）に置き、自己改善ループが書き換えられるようにする。
- **BREAKING**: `prompts.md` の `relevance_score_prompt` は使われなくなる（読み込みは許容するが無視する）。

## Capabilities

### New Capabilities
- `article-selection`: 本文取得後の記事を、要約する価値の判定とトピック別本数の制御によって絞り込む振る舞い。

### Modified Capabilities
- `information-collection`: 「LLM-based relevance scoring」を、型付き判定モデルによる段階評価スコアとトピック判定に置き換える。
- `self-improvement`: 改善提案が変更できる対象に、判定基準のセクション（`relevance_criteria`、`worth_criteria`）とトピック別本数（`topic_quotas`）を加える。

## Impact

- **コード**: `src/tech_curation/collect/nodes/merge_filter.py`、`src/tech_curation/collect/nodes/select.py`、`src/tech_curation/config/settings.py`、新規 `src/tech_curation/jev.py`、`src/tech_curation/improve/nodes/generate_changes.py`・`revise_proposal.py`（変更可能キーの説明）
- **設定**: `vault/agent-config/prompts.md` に `relevance_criteria` / `worth_criteria` / `topic_quotas` セクションを追加
- **依存関係**: `typesafe-sdk` を追加（`httpx2`・`pydantic` などが間接依存として入る）
- **実行環境**: 収集 Lambda に `TYPESAFE_API_KEY` を設定する（`DEEPSEEK_API_KEY` と同じ方法で設定）
- **変わらないもの**: 要約・コンテンツ種別判定・review / revise は DeepSeek のまま
- **後続の変更**: `topic-grouping-dedup` がこの変更の Select ノードを拡張する
