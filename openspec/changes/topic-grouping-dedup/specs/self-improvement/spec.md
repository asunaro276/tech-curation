# Spec Delta

## ADDED Requirements

### Requirement: Duplicate feedback drives grouping criteria
改善パイプラインは`dup`フィードバックを、該当日の`items.json`から対象グループのタイトルと記事を引いたうえで分析に含めなければならない（SHALL）。変更提案は、グループ判定の基準（`prompts.md`の`grouping_criteria`セクション）を`prompt_changes`として変更できる。

#### Scenario: Missed duplicates lead to criteria change
- **WHEN** 複数のフィードバックで「同じライブラリのリリースと解説が別々のセクションになっていた」ことを示す`dup`が記入されている
- **THEN** 変更提案の`prompt_changes`に、その種類の記事を同じ話題とみなすよう書き換えた`grouping_criteria`が含まれ、`prompts.md`に書き戻される

#### Scenario: Dup feedback without record file
- **WHEN** `dup`フィードバックが記入された日の`items.json`が存在しない
- **THEN** そのフィードバックは通し番号だけで分析に含められ、改善パイプラインはエラーにならない
