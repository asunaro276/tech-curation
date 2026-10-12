# Spec Delta

## Purpose

本文取得後の記事候補から、要約してレポートに載せる記事を選ぶ。各記事を型付きの判定モデルで個別に評価し、トピックごとの本数をコードで制御する。

## ADDED Requirements

### Requirement: Per-article worth judgment
システムは本文取得済みの各記事について、型付き判定モデル（Jev）に「要約する価値があるか」を yes/no の確率として判定させなければならない（SHALL）。判定には記事のタイトル・トピック・ソース・本文を渡し、判定基準は `prompts.md` の `worth_criteria` セクションから読み込む。

#### Scenario: Each article receives a worth probability
- **WHEN** 本文取得済みの記事が5本ある
- **THEN** 5本それぞれに 0.0〜1.0 の worth 確率が付与される

#### Scenario: Criteria come from prompts.md
- **WHEN** `prompts.md` の `worth_criteria` セクションが書き換えられている
- **THEN** 次回の収集実行では書き換え後の基準で判定される

### Requirement: Per-topic quota by code
システムはトピックごとに worth 確率の高い順に記事を並べ、`topic_quotas` で指定された本数 K までを残さなければならない（SHALL）。本数の制御はモデルの出力ではなくコードで行う。`topic_quotas` に記載のないトピックには既定値を用いる。

#### Scenario: Quota is enforced exactly
- **WHEN** `topic_quotas` で Go の上限が 1、Go の候補が4本ある
- **THEN** Go からは worth 確率が最も高い1本だけが残る

#### Scenario: Topic not listed uses default quota
- **WHEN** `topic_quotas` に記載のないトピックの候補がある
- **THEN** そのトピックには既定の上限本数が適用される

### Requirement: Every topic with candidates keeps at least one article
システムは候補が1本以上あるトピックについて、worth 確率にかかわらず少なくとも1本を残さなければならない（SHALL）。

#### Scenario: Low-probability topic still appears
- **WHEN** あるトピックの候補すべての worth 確率が 0.2 未満である
- **THEN** そのトピックから worth 確率が最も高い1本が残る

### Requirement: Selection survives judgment failures
システムは判定モデルの呼び出しが失敗した記事に中立値（0.5）を割り当てて選定を続行しなければならない（SHALL）。判定がすべて失敗した場合も、本数制御を適用して実行を完了する。

#### Scenario: Single judgment failure
- **WHEN** 5本のうち1本で判定モデルの呼び出しがエラーになる
- **THEN** その記事の worth 確率は 0.5 として扱われ、残り4本の判定結果とあわせて選定が完了する

#### Scenario: Judgment service unavailable
- **WHEN** 判定モデルの呼び出しがすべて失敗する
- **THEN** 全記事が worth 確率 0.5 として扱われ、トピック別の本数制御を適用した結果がレポートに使われる
