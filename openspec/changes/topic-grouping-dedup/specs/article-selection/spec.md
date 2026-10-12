# Spec Delta

## MODIFIED Requirements

### Requirement: Per-topic quota by code
システムはトピックごとにグループを代表記事の worth 確率の高い順に並べ、`topic_quotas` で指定された数 K までのグループを残さなければならない（SHALL）。上限は記事数ではなくグループ数に適用し、グループに含まれる関連記事は数に含めない。本数の制御はモデルの出力ではなくコードで行う。`topic_quotas` に記載のないトピックには既定値を用いる。

#### Scenario: Quota is enforced exactly
- **WHEN** `topic_quotas` で Go の上限が 1、Go のグループが4つある
- **THEN** Go からは代表記事の worth 確率が最も高い1グループだけが残る

#### Scenario: Topic not listed uses default quota
- **WHEN** `topic_quotas` に記載のないトピックのグループがある
- **THEN** そのトピックには既定の上限数が適用される

#### Scenario: Related articles do not consume quota
- **WHEN** `topic_quotas` で Claude の上限が 2 で、1つ目のグループに3本、2つ目のグループに1本の記事がある
- **THEN** 2グループ（計4本の記事）がすべて残る
