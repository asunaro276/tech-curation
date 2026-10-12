"""State definition for the information collection pipeline."""
from __future__ import annotations

import operator
from typing import Annotated, NotRequired, TypedDict

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
    # select の Jev 判定とグループ分けで付与される（代表記事にだけ related / follow_of が付く）
    worth: NotRequired[float]          # 要約する価値がある確率
    is_primary: NotRequired[float]     # 一次情報である確率
    related: NotRequired[list["CollectedItem"]]  # 同じグループの代表以外の記事
    follow_of: NotRequired["FollowRef | None"]  # 続報の場合、元になった過去のグループ


class FollowRef(TypedDict):
    date: str   # 元のレポートの日付 YYYY-MM-DD
    no: int     # 元のレポートでの通し番号
    title: str  # 元のグループの代表タイトル


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
