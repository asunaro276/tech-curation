# Spec Delta

## MODIFIED Requirements

### Requirement: Per-article worth judgment
システムは本文取得済みの各記事について、型付き判定モデル（Jev）に「このユーザーが興味を持ちそうか」を yes/no の確率（worth）として判定させなければならない（SHALL）。判定には記事のタイトル・トピック・ソース・本文を渡し、判定基準は `prompts.md` の `worth_criteria` セクションから読み込み、vault の `agent-config/policy.md`（ユーザーの普段の好み）があれば添える。

#### Scenario: Each article receives a worth probability
- **WHEN** 本文取得済みの記事が5本ある
- **THEN** 5本それぞれに 0.0〜1.0 の worth 確率が付与される

#### Scenario: Criteria come from prompts.md
- **WHEN** `prompts.md` の `worth_criteria` セクションが書き換えられている
- **THEN** 次回の収集実行では書き換え後の基準で判定される

#### Scenario: Policy is taken into account
- **WHEN** `policy.md` に「Rails の実務での事例が好き、入門記事は不要」と書かれている
- **THEN** その内容が興味の判定基準に添えられる


### Requirement: Per-topic quota by code
システムはトピックごとにグループを代表記事の worth 確率の高い順に並べ、`topic_quotas` で指定された数 K までのグループを残さなければならない（SHALL）。上限は記事数ではなくグループ数に適用し、グループに含まれる関連記事は数に含めない。リリース情報のグループとトレンド情報の記事は同じ上限を共有し、worth の高い順に選ぶ。本数の制御はモデルの出力ではなくコードで行う。`topic_quotas` に記載のないトピックには既定値を用いる。

#### Scenario: Quota is enforced exactly
- **WHEN** `topic_quotas` で Go の上限が 1、Go のグループが4つある
- **THEN** Go からは代表記事の worth 確率が最も高い1グループだけが残る

#### Scenario: Topic not listed uses default quota
- **WHEN** `topic_quotas` に記載のないトピックのグループがある
- **THEN** そのトピックには既定の上限数が適用される

#### Scenario: Related articles do not consume quota
- **WHEN** `topic_quotas` で Claude の上限が 2 で、1つ目のグループに3本、2つ目のグループに1本の記事がある
- **THEN** 2グループ（計4本の記事）がすべて残る
