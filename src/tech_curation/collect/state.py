"""State definition for the information collection pipeline."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from tech_curation.config.settings import AgentConfig


class CollectedItem(TypedDict):
    id: str
    title: str
    url: str
    source: str         # github | rss | hackernews | substack
    published: str      # ISO 8601 date string
    body: str           # raw text / description
    relevance_score: float
    summary: str
    content_type: str   # code | comparison | trend
    thumbnail: str      # og:image URL (empty string if unavailable)
    topic: str          # assigned topic from merge_filter (empty string if unmatched)


class ReviewIssue(TypedDict):
    item_index: int
    action: str   # "remove" | "rewrite"
    reason: str
    rewrite_hint: str


class CollectState(TypedDict):
    topics: list[str]
    config: AgentConfig
    queries: dict[str, list[str]]                           # topic -> list of search queries
    raw_items: Annotated[list[CollectedItem], operator.add]  # fan-out nodes append independently
    filtered_items: list[CollectedItem]                      # after dedup + date + relevance filter
    formatted_items: list[CollectedItem]                     # after summarize & format
    review_issues: list[ReviewIssue]                         # issues found in review
    review_iterations: int                                   # loop counter
    errors: Annotated[list[str], operator.add]               # fan-out nodes append independently
