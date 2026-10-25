# Agent Config

## source_weights

- github: 0.8
- rss: 0.6
- hackernews: 0.5
- substack: 0.4

## filter_threshold

filter_threshold: 0.5

## recency_days

recency_days: 7

## max_items_per_run

max_items_per_run: 30

## query_gen_prompt

Generate 3 concise search queries for the given topic that would surface recent, high-quality technical content.
Output as a JSON array of strings. Example: ["query 1", "query 2", "query 3"]

## relevance_score_prompt

Score the relevance of this article to the given topics on a scale from 0.0 to 1.0.
0.0 = completely unrelated, 1.0 = exactly on topic.
Consider technical depth and recency. Return only a JSON number.

## summarize_prompt

Summarize this article in 2–3 sentences focusing on key technical insights and practical takeaways.
Return only the summary text, no preamble.

## content_type_prompt

Classify this content as exactly one of: code, comparison, trend.
- code: contains code examples, library releases, implementation details
- comparison: benchmarks, trade-off analyses, tool comparisons
- trend: ecosystem trends, community surveys, adoption patterns
Return only the single word.

## relevance_criteria

- 0: 関心トピックと無関係
- 1: トピックの名前が出てくるだけで、技術的な内容はほとんどない
- 2: トピックに関係する技術内容を一部含む
- 3: トピックの技術内容が主題になっている
- 4: トピックの中心的な技術内容（新機能・リリース・実装・検証）を具体的に扱っている

## worth_criteria

このユーザーはこの記事に興味を持ちそうか。関心トピックの具体的な技術変更・新機能・実装例・リリース情報・breaking change・脆弱性情報やセキュリティアドバイザリ・独自の比較や検証・コードやベンチマークを含む記事は yes。内容がほぼ空、タイトルと本文が一致しない、宣伝だけ、初心者向けの一般的な入門だけの記事は no。

## grouping_criteria

この記事は、選択肢のどのリリース・発表と同じか。同じソフトウェアの同じバージョン・同じ発表を扱う記事は同じとする。例: 公式リリースノートと、そのリリースの解説記事・まとめ記事。同じソフトウェアでも別のバージョンや別の発表は別とする。過去に掲載したリリースに新しい情報が加わったもの（RC から正式版、パッチ版、追加の発表）は同じではなく続報とする。

## topic_quotas

- Go: 1
- TypeScript/JavaScript: 2
- Ruby: 2
- Ruby on Rails: 2
- Claude: 3
- vue: 2
- postgresql: 3
- セキュリティ: 3
- トレンド: 5
- default: 2

## 改善履歴

| date | reason |
|------|--------|
