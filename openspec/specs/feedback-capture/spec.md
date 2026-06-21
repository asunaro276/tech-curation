## ADDED Requirements

### Requirement: HTML comment feedback parsing
システムはMarkdownファイル内の`<!-- fb: relevance=<N>, comment=<text> -->`形式のコメントを正規表現でパースし、構造化データに変換しなければならない（SHALL）。

#### Scenario: Valid feedback comment is parsed
- **WHEN** ファイルに`<!-- fb: relevance=4, comment=参考になった -->`が含まれる
- **THEN** `{item_id: "001", relevance: 4, comment: "参考になった"}`として抽出される

#### Scenario: Empty feedback comment is skipped
- **WHEN** `<!-- fb: relevance=, comment= -->`（未記入）のコメントが存在する
- **THEN** そのアイテムはフィードバックなしとして扱い、パース結果から除外される

### Requirement: Feedback submission via Obsidian Button to API Gateway
ユーザーがObsidianのButtonプラグインのフィードバック送信ボタンをクリックすると、Shell Commands PluginがAPI GatewayエンドポイントへHTTP POSTリクエストを送信しなければならない（SHALL）。

#### Scenario: Button triggers API Gateway
- **WHEN** ユーザーが「フィードバックを送信」ボタンをクリックする
- **THEN** Shell Commands Pluginが`curl -X POST <API_GATEWAY_URL>/improve -d '{"note_path": "<note_path>"}'`を実行し、改善LambdaがトリガーされるHTTPレスポンスを受け取る

### Requirement: Status update after submission
フィードバック送信後、改善Lambdaはob sync経由でノートのfrontmatter内statusを`submitted`に更新しなければならない（SHALL）。

#### Scenario: Status changes to submitted
- **WHEN** 改善LambdaがフィードバックのパースとLangGraph改善パイプラインを完了する
- **THEN** 対象ノートのfrontmatterのstatusが`submitted`に書き換えられob sync pushでvaultに反映される

### Requirement: Feedback history persistence
システムはパース済みフィードバックを履歴として`vault/agent-config/feedback-history.json`に追記しなければならない（SHALL）。追記は改善Lambdaがob sync経由で行う。

#### Scenario: Feedback is appended to history
- **WHEN** 改善LambdaがフィードバックのパースとLangGraph改善パイプラインを完了する
- **THEN** パース結果がタイムスタンプ・ノートパスとともにfeedback-history.jsonに追記されob sync pushでvaultに反映される
