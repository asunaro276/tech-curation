# information-collection Specification

## Purpose

設定されたトピックについて GitHub・RSS などの複数のソースから技術記事を並列に収集し、重複除去・日付・関連度によって絞り込む。

## Requirements

### Requirement: Parallel multi-source collection
システムはGitHub API・RSS・HackerNews・Substackの各ソースを並列に収集するLangGraphパイプラインを持たなければならない（SHALL）。各ソースはLangGraphの独立したノードとして実装し、Merge&Filterノードで統合する。

#### Scenario: Parallel fetch completes
- **WHEN** 収集パイプラインが起動される
- **THEN** GitHub・RSS・HackerNews・Substackの各ノードが並列実行され、全ノードの結果がMerge&Filterノードに渡される

#### Scenario: Partial source failure
- **WHEN** いずれかのソースのAPI呼び出しが失敗する
- **THEN** 失敗したソースの結果は空リストとして扱い、他ソースの収集結果でパイプラインを継続する

### Requirement: Source weight configuration
システムはagent_config内のsource_weightsに基づいて、各ソースへの収集アイテム数の上限を決定しなければならない（SHALL）。

#### Scenario: High-weight source gets more items
- **WHEN** github weight=0.9、hackernews weight=0.3 が設定されている
- **THEN** GitHubからの収集上限がHackerNewsより多く割り当てられる

### Requirement: LLM-based query generation
システムはPlanノードでLLMを使用してトピックから検索クエリ群を生成しなければならない（SHALL）。クエリ生成にはagent_config内のquery_gen_promptを使用する。

#### Scenario: Query generation from topic
- **WHEN** topic="Rust async ecosystem" でパイプラインが起動される
- **THEN** LLMが複数の検索クエリ（例: "tokio 2026 release", "rust async runtime comparison"）を生成して返す

### Requirement: Deduplication and date filtering
システムはURL重複除去およびrecency_days設定に基づく日付フィルタリングをScriptで行わなければならない（SHALL）。

#### Scenario: Duplicate URL removal
- **WHEN** 複数ソースから同一URLのアイテムが収集される
- **THEN** 重複するURLのアイテムは1件のみ残し、残りは除外される

#### Scenario: Old item filtering
- **WHEN** recency_days=7 が設定されており、8日前のアイテムが存在する
- **THEN** そのアイテムはフィルタリングで除外される

### Requirement: LLM-based relevance scoring
システムは型付き判定モデル（Jev）の段階評価（Score）を使用して各アイテムのトピックへの関連度をスコアリングし、filter_threshold未満のアイテムを除外しなければならない（SHALL）。段階評価の各段階の説明は`prompts.md`の`relevance_criteria`セクションから読み込み、期待スコアを0.0〜1.0に正規化した値を関連度とする。判定が失敗したアイテムの関連度は0.5とする。

#### Scenario: Low relevance item excluded
- **WHEN** filter_threshold=0.5 が設定されており、判定モデルの正規化後の関連度が0.3のアイテムが存在する
- **THEN** そのアイテムはMerge&Filterノードで除外される

#### Scenario: Relevance is normalized from rubric levels
- **WHEN** `relevance_criteria`が5段階（0〜4）で定義され、判定モデルの期待スコアが3.0である
- **THEN** そのアイテムの関連度は0.75として扱われる

#### Scenario: Scoring failure falls back to neutral
- **WHEN** あるアイテムの判定モデル呼び出しがエラーになる
- **THEN** そのアイテムの関連度は0.5として扱われ、パイプラインは継続する

### Requirement: Topic list from topics.md
システムは収集対象トピックを`vault/agent-config/topics.md`から読み込まなければならない（SHALL）。ob sync pullで取得し、「アクティブ」セクションに記載されたトピックのみを収集対象とする。

#### Scenario: Active topics are collected
- **WHEN** topics.mdにアクティブなトピックが3件記載されている
- **THEN** 収集パイプラインはその3件それぞれに対してPlanノードを実行する

#### Scenario: Paused topics are skipped
- **WHEN** topics.mdの「停止中」セクションにトピックが記載されている
- **THEN** そのトピックは収集対象から除外される

### Requirement: HackerNews via RSS
HackerNewsはRSS（`https://news.ycombinator.com/rss`）を使用し、feedparserで他のRSSフィードと同一ノードで処理しなければならない（SHALL）。

#### Scenario: HackerNews items fetched via RSS node
- **WHEN** 収集パイプラインが起動される
- **THEN** HackerNewsのRSSフィードがfeedparserで取得され、RSSノードの結果として返される

### Requirement: Scheduled execution via EventBridge and Lambda
収集パイプラインはAWS EventBridgeによるスケジュールトリガーでLambda上で実行されなければならない（SHALL）。Lambdaはコンテナイメージとして実装し、実行時間は15分以内に収まるよう設計する。

#### Scenario: Scheduled trigger fires
- **WHEN** EventBridgeの設定した時刻になる
- **THEN** Lambdaが起動し、ob sync pullでtopics.md・prompts.mdを取得してから収集パイプラインが実行される

### Requirement: Topic assignment by typed judgment
システムはRSSフィードのトピックヒントを持たないアイテムについて、関連度と同じ判定モデル呼び出しの中で、アクティブなトピックのいずれに属するかを選択式（Choice）で判定しなければならない（SHALL）。どの個別トピックにも当てはまらないアイテムは「トレンド」に割り当てる。

#### Scenario: Article without feed hint is classified
- **WHEN** トピックヒントのないアイテム「Go 1.25 の iter パッケージ解説」が収集される
- **THEN** 判定モデルがトピック「Go」を選び、そのアイテムは Go のトピックに割り当てられる

#### Scenario: Feed hint takes precedence
- **WHEN** Ruby 専用フィードから収集されたアイテムにトピックヒント「Ruby」が付いている
- **THEN** 判定モデルの選択結果にかかわらず、そのアイテムは Ruby のトピックに割り当てられる

#### Scenario: Unmatched article goes to trend
- **WHEN** 判定モデルがどの個別トピックにも当てはまらないと判定する
- **THEN** そのアイテムは「トレンド」に割り当てられる
