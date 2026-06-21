## ADDED Requirements

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
システムはLLMを使用して各アイテムのトピックへの関連度をスコアリングし、filter_threshold未満のアイテムを除外しなければならない（SHALL）。

#### Scenario: Low relevance item excluded
- **WHEN** filter_threshold=0.5 が設定されており、LLMが関連度0.3と判定したアイテムが存在する
- **THEN** そのアイテムはMerge&Filterノードで除外される

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
