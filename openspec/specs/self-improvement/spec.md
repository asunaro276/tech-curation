# self-improvement Specification

## Purpose

フィードバックを分析して収集エージェントの設定（重み・閾値・プロンプト・トピック）を改善し、vault に書き戻す。

## Requirements

### Requirement: Script-based pattern statistics
システムはパース済みフィードバックからソース別平均スコア等の統計をScriptで計算しなければならない（SHALL）。

#### Scenario: Per-source average is computed
- **WHEN** フィードバック履歴に複数ソースのアイテム評価が存在する
- **THEN** 各ソースのrelevance平均スコアが計算される（例: github_avg=4.2, hackernews_avg=1.8）

### Requirement: LLM-based qualitative pattern analysis
システムはフィードバックコメントの質的パターン（ユーザーの好み・嫌い）をLLMで解釈しなければならない（SHALL）。

#### Scenario: Qualitative preference is identified
- **WHEN** 複数のコメントに「実装例が良い」「議論系は不要」等の記述が存在する
- **THEN** LLMが「実装例・パフォーマンス系を好む、意見・議論系を嫌う」というパターンを抽出する

### Requirement: Structured JSON change proposal by LLM
システムはGenerateChangesノードでLLMが変更内容を構造化JSONで出力しなければならない（SHALL）。JSONはparam_changesとprompt_changesとreasonフィールドを持つ。

#### Scenario: Numeric parameter adjustment is proposed
- **WHEN** hackernews_avg=1.8（低評価）が検出される
- **THEN** LLMが`{"param_changes": {"source_weights.hackernews": 0.2}, "prompt_changes": null, "reason": "HNの平均評価が低いため"}`を出力する

#### Scenario: Prompt change is proposed only for qualitative shift
- **WHEN** 統計変化ではなく「情報の種類の定義」が変わったとLLMが判断する
- **THEN** LLMがprompt_changesに更新後のプロンプトテキストを含むJSONを出力する

### Requirement: Script applies LLM change proposal to config
システムはApplyChangesノードでLLMのJSON出力をScriptが読み取り、`vault/agent-config/prompts.md`を更新しなければならない（SHALL）。

#### Scenario: Numeric parameter is updated in config
- **WHEN** param_changes に`{"source_weights.hackernews": 0.2}`が含まれる
- **THEN** prompts.md内のhackernews weightが0.2に書き換えられる

#### Scenario: Change is logged in improvement history
- **WHEN** configの更新が完了する
- **THEN** prompts.md内の改善履歴テーブルに変更内容・日付・reasonが追記される

### Requirement: Improvement Lambda triggered by API Gateway
改善パイプラインはAPI GatewayへのHTTP POSTリクエストによってトリガーされるLambda上で実行されなければならない（SHALL）。収集LambdaとコンテナイメージはGo共有し、ハンドラーのみ分離する。

#### Scenario: API Gateway triggers improvement Lambda
- **WHEN** API Gatewayが`/improve`エンドポイントへのPOSTリクエストを受信する
- **THEN** 改善Lambda（handler_improve）が起動し、LangGraph改善パイプラインが実行される

#### Scenario: Lambda reads feedback via ob sync
- **WHEN** 改善Lambdaが起動する
- **THEN** ob sync pullでvaultの最新状態（フィードバックファイル・prompts.md・feedback-history.json）を取得してからパイプラインを開始する

### Requirement: Config pushed back to Obsidian Sync after improvement
改善後の`vault/agent-config/prompts.md`はob sync pushを通じてObsidian Syncへ書き戻されなければならない（SHALL）。次回の収集Lambdaはob sync pullで最新のprompts.mdを参照する。

#### Scenario: Updated config is pushed by improvement Lambda
- **WHEN** 改善LambdaがApplyChangesノードでprompts.mdの更新を完了する
- **THEN** ob sync pushが実行されObsidian Syncに反映され、次回収集Lambda実行時に最新設定が使用される

### Requirement: Judgment criteria are improvable
改善パイプラインの変更提案は、判定モデルに渡す判定基準のセクション（`relevance_criteria`、`worth_criteria`）を`prompt_changes`として、トピック別の残す本数（`topic_quotas`）を`param_changes`として変更できなければならない（SHALL）。ApplyChangesノードはこれらを`prompts.md`の該当セクションに書き戻す。

#### Scenario: Worth criteria are rewritten
- **WHEN** フィードバックで「入門記事は不要」というパターンが検出され、変更提案の`prompt_changes`に`worth_criteria`が含まれる
- **THEN** `prompts.md`の`worth_criteria`セクションが提案の内容に書き換えられる

#### Scenario: Topic quota is adjusted
- **WHEN** 変更提案の`param_changes`に`{"topic_quotas.Go": 2}`が含まれる
- **THEN** `prompts.md`の`topic_quotas`セクションで Go の上限が2に書き換えられる
