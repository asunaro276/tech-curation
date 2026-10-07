# Spec Delta

## ADDED Requirements

### Requirement: Judgment criteria are improvable
改善パイプラインの変更提案は、判定モデルに渡す判定基準のセクション（`relevance_criteria`、`worth_criteria`）を`prompt_changes`として、トピック別の残す本数（`topic_quotas`）を`param_changes`として変更できなければならない（SHALL）。ApplyChangesノードはこれらを`prompts.md`の該当セクションに書き戻す。

#### Scenario: Worth criteria are rewritten
- **WHEN** フィードバックで「入門記事は不要」というパターンが検出され、変更提案の`prompt_changes`に`worth_criteria`が含まれる
- **THEN** `prompts.md`の`worth_criteria`セクションが提案の内容に書き換えられる

#### Scenario: Topic quota is adjusted
- **WHEN** 変更提案の`param_changes`に`{"topic_quotas.Go": 2}`が含まれる
- **THEN** `prompts.md`の`topic_quotas`セクションで Go の上限が2に書き換えられる
