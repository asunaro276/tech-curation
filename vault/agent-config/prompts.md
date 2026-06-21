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

## 改善履歴

| date | reason |
|------|--------|
