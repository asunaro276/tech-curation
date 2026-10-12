# Spec Delta

## MODIFIED Requirements

### Requirement: LLM-based relevance scoring
システムは型付き判定モデル（Jev）の段階評価（Score）を使用して各アイテムのトピックへの関連度をスコアリングし、filter_threshold未満のアイテムを除外しなければならない（SHALL）。ただし「トレンド」に割り当てられたアイテムはどの個別トピックにも当てはまらないことが前提のため、filter_thresholdを適用しない。段階評価の各段階の説明は`prompts.md`の`relevance_criteria`セクションから読み込み、期待スコアを0.0〜1.0に正規化した値を関連度とする。判定が失敗したアイテムの関連度は0.5とする。

#### Scenario: Low relevance item excluded
- **WHEN** filter_threshold=0.5 が設定されており、判定モデルの正規化後の関連度が0.3で、トピック「Go」に割り当てられたアイテムが存在する
- **THEN** そのアイテムはMerge&Filterノードで除外される

#### Scenario: Trend item is not filtered by relevance
- **WHEN** filter_threshold=0.5 が設定されており、「トレンド」に割り当てられたアイテムの関連度が0.05である
- **THEN** そのアイテムは関連度では除外されず、トレンドの候補として残る

#### Scenario: Relevance is normalized from rubric levels
- **WHEN** `relevance_criteria`が5段階（0〜4）で定義され、判定モデルの期待スコアが3.0である
- **THEN** そのアイテムの関連度は0.75として扱われる

#### Scenario: Scoring failure falls back to neutral
- **WHEN** あるアイテムの判定モデル呼び出しがエラーになる
- **THEN** そのアイテムの関連度は0.5として扱われ、パイプラインは継続する

### Requirement: Topic assignment by typed judgment
システムは関連度と同じ判定モデル呼び出しの中で、各アイテムがアクティブなトピックのいずれに属するかを選択式（Choice）で判定し、その結果をトピックとして割り当てなければならない（SHALL）。RSSフィードのトピックヒントとキーワードマッチは、判定モデルの呼び出しが失敗した場合にのみ、この順で用いる。どの個別トピックにも当てはまらないアイテムは「トレンド」に割り当てる。

#### Scenario: Article without feed hint is classified
- **WHEN** トピックヒントのないアイテム「Go 1.25 の iter パッケージ解説」が収集される
- **THEN** 判定モデルがトピック「Go」を選び、そのアイテムは Go のトピックに割り当てられる

#### Scenario: Judgment takes precedence over feed hint
- **WHEN** Ruby 用フィードから収集された Rails の記事にトピックヒント「Ruby」が付いており、判定モデルが「Ruby on Rails」を選ぶ
- **THEN** そのアイテムは Ruby on Rails のトピックに割り当てられる

#### Scenario: Feed hint takes precedence
- **WHEN** トピックヒント「Ruby」が付いたアイテムで判定モデルの呼び出しがエラーになり、キーワードマッチでは「Go」に一致する
- **THEN** フィードのヒントがキーワードマッチより優先され、そのアイテムは Ruby のトピックに割り当てられる

#### Scenario: Unmatched article goes to trend
- **WHEN** 判定モデルがどの個別トピックにも当てはまらないと判定する
- **THEN** そのアイテムは「トレンド」に割り当てられる

## ADDED Requirements

### Requirement: Per-feed item limit
システムは `feeds.md` のフィード行の末尾に `{max=N}` が指定されている場合、そのフィードから取り込む記事を最新の N 件までとしなければならない（SHALL）。指定がないフィードは、フィード数とソースの重みから決まる既定の件数とする。

#### Scenario: Aggregator feed with explicit limit
- **WHEN** `feeds.md` に `- https://yamadashy.github.io/tech-blog-rss-feed/feeds/rss.xml {max=50}` と書かれている
- **THEN** そのフィードからは最新の 50 件までが取り込まれる

#### Scenario: Feed without limit
- **WHEN** `feeds.md` に `- https://rubyweekly.com/rss/ [Ruby]` と書かれている
- **THEN** そのフィードからは既定の件数が取り込まれる

### Requirement: Trend candidates from any non-repository source
システムは「トレンド」に割り当てられた記事のうち、GitHub のリポジトリ以外のすべての記事をトレンドの候補としなければならない（SHALL）。トレンドの候補は他のトピックより多めに選定へ渡す。

#### Scenario: Company tech blog article becomes a trend candidate
- **WHEN** 企業テックブログのまとめフィードの記事が「トレンド」に割り当てられる
- **THEN** その記事はトレンドの候補になる

#### Scenario: GitHub repository is not a trend candidate
- **WHEN** GitHub のリポジトリが「トレンド」に割り当てられる
- **THEN** そのリポジトリはトレンドの候補にならない
