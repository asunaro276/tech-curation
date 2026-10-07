# Spec Delta

## MODIFIED Requirements

### Requirement: HTML comment feedback parsing
システムはMarkdownファイル内の`<!-- fb: relevance=<N>, dup=<D>, comment=<text> -->`形式のコメントを正規表現でパースし、構造化データに変換しなければならない（SHALL）。`dup`は任意項目であり、`dup`を含まない旧形式`<!-- fb: relevance=<N>, comment=<text> -->`も引き続きパースする。`dup`には同じ話題だった今日のセクションの通し番号、または過去に読んだことを表す`past`を記入する。

#### Scenario: Valid feedback comment is parsed
- **WHEN** ファイルに`<!-- fb: relevance=4, comment=参考になった -->`が含まれる
- **THEN** `{item_id: "001", relevance: 4, comment: "参考になった"}`として抽出される

#### Scenario: Empty feedback comment is skipped
- **WHEN** `<!-- fb: relevance=, dup=, comment= -->`（未記入）のコメントが存在する
- **THEN** そのアイテムはフィードバックなしとして扱い、パース結果から除外される

#### Scenario: Duplicate of another section
- **WHEN** 通し番号 5 のセクションに`<!-- fb: relevance=, dup=3, comment= -->`が記入されている
- **THEN** 通し番号 5 のフィードバックとして「通し番号 3 と同じ話題」が抽出される

#### Scenario: Already read in the past
- **WHEN** `<!-- fb: relevance=2, dup=past, comment= -->`が記入されている
- **THEN** relevance=2 とともに「過去に読んだ話題」が抽出される
