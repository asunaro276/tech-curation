# Spec Delta

## MODIFIED Requirements

### Requirement: Per-item Markdown report generation
システムは選定済みのグループを1グループ1セクション形式のMarkdownレポートとして生成しなければならない（SHALL）。各セクションには通し番号・代表記事のタイトル・ソース・日付・グループの統合要約・グループ内の全記事へのリンク・HTMLコメント形式のフィードバック欄を含める。

#### Scenario: Report contains all required fields
- **WHEN** 選定済みグループのリストからレポートが生成される
- **THEN** 各セクションに通し番号・代表記事のタイトルとURL・ソース名・収集日・統合要約・関連記事のリンク一覧・`<!-- fb: relevance=, dup=, comment= -->`が含まれる

#### Scenario: Button for feedback submission is included
- **WHEN** レポートが生成される
- **THEN** ファイル末尾にObsidian Buttonプラグイン形式のフィードバック送信ボタンが含まれる

#### Scenario: Single-article group has one link
- **WHEN** 記事が1本だけのグループのセクションが生成される
- **THEN** 関連記事のリンク一覧には代表記事のリンク1件だけが含まれる

## ADDED Requirements

### Requirement: Follow-up link to previous report
システムは続報と判定されたグループのセクションに、元になった過去のレポートへのリンクと、そのグループの代表タイトルを表示しなければならない（SHALL）。

#### Scenario: Follow-up section shows previous report
- **WHEN** 「Go 1.25 正式リリース」が 2026-10-01 のレポートの「Go 1.25 RC」の続報として選定される
- **THEN** そのセクションに 2026-10-01 のレポートへのリンクと「Go 1.25 RC」というタイトルが表示される

### Requirement: Daily group record persistence
システムはレポートと同じ日付のディレクトリに、その日に載せたグループの記録（`items.json`）を保存しなければならない（SHALL）。記録には各グループの通し番号・トピック・代表タイトル・要約・所属記事のタイトルとURL・続報の参照先を含める。

#### Scenario: Record is written with the report
- **WHEN** 2026-10-06 のレポートが生成される
- **THEN** `tech-curation/2026-10-06/items.json` が保存され、ob sync push で vault に反映される

#### Scenario: Record matches report numbering
- **WHEN** レポートの通し番号 3 のセクションが「Go 1.25 リリース」である
- **THEN** `items.json` の通し番号 3 のグループも「Go 1.25 リリース」である
