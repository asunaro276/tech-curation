## ADDED Requirements

### Requirement: Per-item Markdown report generation
システムはフィルタリング済みアイテムを1アイテム1セクション形式のMarkdownレポートとして生成しなければならない（SHALL）。各アイテムにはタイトル・ソース・日付・要約・HTMLコメント形式のフィードバック欄を含める。

#### Scenario: Report contains all required fields
- **WHEN** フィルタリング済みアイテムリストからレポートが生成される
- **THEN** 各アイテムセクションにタイトル・URL・ソース名・収集日・LLM要約・`<!-- fb: relevance=, comment= -->`が含まれる

#### Scenario: Button for feedback submission is included
- **WHEN** レポートが生成される
- **THEN** ファイル末尾にObsidian Buttonプラグイン形式のフィードバック送信ボタンが含まれる

### Requirement: YAML frontmatter with status field
生成されるMarkdownファイルはYAMLフロントマターを持たなければならない（SHALL）。frontmatterにはdate・topic・agent_version・statusフィールドを含める。statusの初期値は`draft`とする。

#### Scenario: Frontmatter is valid YAML
- **WHEN** レポートファイルが生成される
- **THEN** ファイル先頭のYAML frontmatterがdate・topic・agent_version・status=draftを含む

### Requirement: Output via obsidian-headless sync
システムはobsidian-headlessの`ob sync`コマンドを使用してObsidian Syncへレポートを書き出さなければならない（SHALL）。Lambda起動時のob loginクレデンシャルはAWS Secrets Managerから取得する。

#### Scenario: File appears in Obsidian vault
- **WHEN** Lambdaがレポート生成後にob syncを実行する
- **THEN** 生成されたMarkdownファイルがObsidian Syncを通じてユーザーのvaultに同期される

#### Scenario: Secrets Manager credential retrieval
- **WHEN** LambdaがSecrets Managerからob loginクレデンシャルを取得する
- **THEN** 取得したクレデンシャルを使用してob syncが認証成功する

### Requirement: Dynamic format routing
システムはアイテムのコンテンツ種別（code/comparison/trend）をLLMで判定し、種別に応じたフォーマットテンプレートを適用しなければならない（SHALL）。

#### Scenario: Code content gets code-focused format
- **WHEN** アイテムがリリースノートやコード例を含むとLLMが判定する
- **THEN** コードハイライト付きのフォーマットテンプレートが適用される

#### Scenario: Trend content gets trend format
- **WHEN** アイテムがエコシステムトレンドに関するものとLLMが判定する
- **THEN** トレンド概要フォーマットテンプレートが適用される
