# Spec Delta

## Purpose

同じ出来事や話題を扱う記事を1つのグループにまとめ、前日以前のレポートに載った話題との重複と続報を見分け、各グループの代表記事を選ぶ。

## ADDED Requirements

### Requirement: Greedy topic grouping
システムはトピックごとに候補記事を worth 確率の降順に1本ずつ処理し、判定モデル（Jev）の選択式判定で「新しいグループ」か「既存のどのグループと同じ話題か」を決めなければならない（SHALL）。一度決めた所属は後から変更しない。同じ出来事（特定のリリース・発表・不具合など）を扱う記事と、同じ連載の別の回は同じ話題とみなす。テーマが近いだけの記事は同じ話題とみなさない。

#### Scenario: Release note and explainer are grouped
- **WHEN** Go の候補に「Go 1.25 Release Notes」（公式）と「Go 1.25 の新機能まとめ」（Zenn）がある
- **THEN** 2本は同じグループに入る

#### Scenario: Different subjects stay separate
- **WHEN** Go の候補に「Go 1.25 の新機能まとめ」と「sqlc で型安全な SQL」がある
- **THEN** 2本は別々のグループになる

#### Scenario: Series episodes are grouped
- **WHEN** 候補に「35日でフロントエンドの基礎を完全に理解する #4」と「同 #5」がある
- **THEN** 2本は同じグループに入る

#### Scenario: Theme-only similarity stays separate
- **WHEN** 候補に「AI時代のエンジニア技能維持を航空業界に学ぶ」と「若手エンジニアに必要な『AIを使う力』」がある
- **THEN** 2本は別々のグループになる

#### Scenario: First article needs no judgment
- **WHEN** あるトピックで最初に処理する記事である
- **THEN** 判定モデルを呼ばずに新しいグループを作る

### Requirement: Merges are confirmed pairwise
システムは選択式の判定で既存のグループ（今日のグループ、または過去と同じ話題）が選ばれた場合、その記事とグループの代表となる記事の2本だけを比べる判定で同じ話題であることを確かめなければならない（SHALL）。確認できない場合（確率 0.5 未満、または判定の失敗）は、その記事を新しいグループとして扱う。

#### Scenario: Unrelated nearest group is rejected
- **WHEN** 連載「35日でフロントエンド #5」がまだ #4 のグループがない時点で処理され、選択式の判定が無関係な「Tisilia を公開」のグループを選ぶ
- **THEN** 1対1の判定で同じ話題と確認されないため、#5 は新しいグループになり、後から処理される #4 はそのグループに入れる

#### Scenario: Confirmed merge
- **WHEN** 選択式の判定が「DHH 回（#35 解説）」のグループを選び、1対1の判定でも同じ話題と確認される
- **THEN** 記事はそのグループに入る

### Requirement: Grouping is limited to the same topic
システムはグループ分けを同じトピックに割り当てられた記事の間でのみ行わなければならない（SHALL）。異なるトピックの記事が同じグループに入ることはない。

#### Scenario: Cross-topic articles are not merged
- **WHEN** 「Claude Code で Rails アプリを移行した」が Claude に、「Rails 8 の新機能」が Ruby on Rails に割り当てられている
- **THEN** 2本は別々のグループになる

### Requirement: Past report deduplication
システムは過去 `recency_days` 日分のグループ記録を判定の選択肢に含め、過去と同じ話題と判定された記事を除外しなければならない（SHALL）。過去のレポートに載った URL と同じ URL の記事は、判定モデルを呼ばずに除外する。

#### Scenario: Topic already reported yesterday
- **WHEN** 前日のレポートに「Go 1.25 リリース」のグループがあり、今日の候補に同じリリースの別の解説記事がある
- **THEN** その記事は今日のレポートから除外される

#### Scenario: Same URL reported before
- **WHEN** 3日前のレポートに載った URL の記事が今日も候補にある
- **THEN** その記事は判定モデルを呼ばずに除外される

#### Scenario: No past records exist
- **WHEN** 過去のグループ記録が1件もない
- **THEN** 今日の候補だけでグループ分けが行われ、エラーにならない

### Requirement: Follow-up articles are kept
システムは過去の話題の続報（RC から正式版、続編、追加の発表など）と判定された記事を除外せず、新しいグループとして残し、元になった過去のレポートの日付とグループを記録しなければならない（SHALL）。

#### Scenario: GA after RC
- **WHEN** 前日のレポートに「Go 1.25 RC」があり、今日の候補に「Go 1.25 正式リリース」がある
- **THEN** 「Go 1.25 正式リリース」は続報として残り、前日のレポートと「Go 1.25 RC」のグループへの参照を持つ

### Requirement: Representative selection
システムは各グループの代表記事を、一次情報である記事、日本語の記事、worth 確率の高い記事の優先順で選ばなければならない（SHALL）。一次情報は公式のドキュメント・ブログ・リリースノート・アナウンスを指し、個人の解説記事・体験記・まとめ記事は含めない。一次情報かどうかは判定モデルで判定し、日本語かどうかは本文・タイトルに仮名が含まれるかで判定する。

#### Scenario: Primary source wins over higher worth
- **WHEN** グループに公式リリースノート（一次情報・英語・worth 0.80）と Zenn の解説（二次情報・日本語・worth 0.91）がある
- **THEN** 公式リリースノートが代表になる

#### Scenario: Japanese wins among secondary sources
- **WHEN** グループに英語のブログ（二次情報・worth 0.85）と Qiita の記事（二次情報・日本語・worth 0.70）がある
- **THEN** Qiita の記事が代表になる

### Requirement: Integrated group summary
システムはグループごとに、代表記事と関連記事の内容を合わせた1本の要約を生成しなければならない（SHALL）。要約には、関連記事にしか書かれていない観点も含める。

#### Scenario: Group with three articles
- **WHEN** 公式リリースノート・Zenn の解説・Qiita の記事からなるグループを要約する
- **THEN** 3本の内容を統合した1本の要約が生成される

#### Scenario: Single-article group
- **WHEN** グループに記事が1本しかない
- **THEN** その記事だけから要約が生成される

### Requirement: Grouping survives judgment failures
システムはグループ判定の呼び出しが失敗した記事を新しいグループとして扱い、処理を続行しなければならない（SHALL）。

#### Scenario: Judgment error during grouping
- **WHEN** ある記事のグループ判定で判定モデルの呼び出しがエラーになる
- **THEN** その記事は新しいグループとなり、残りの記事のグループ分けが続行される
