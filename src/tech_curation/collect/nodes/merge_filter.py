"""Merge & Filter node: dedup, date filter, and LLM relevance scoring."""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.llm import chat

MAX_WORKERS = 12

# トピック名だけでは拾えない別名・略称
_TOPIC_EXTRAS: dict[str, list[str]] = {
    "go": ["golang"],
    "ruby on rails": ["rails"],
    "vue": ["vue.js", "vuejs"],
    "postgresql": ["postgres"],
    "claude": ["anthropic"],
    "node.js": ["nodejs", "node"],
    "react": ["react.js", "reactjs", "next.js", "nextjs"],
}


def _topic_patterns(topic: str) -> list[re.Pattern]:
    keywords = [topic.lower()] + _TOPIC_EXTRAS.get(topic.lower(), [])
    return [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]


def _assign_topic(item: CollectedItem, topics: list[str]) -> str | None:
    """タイトル→本文の順でキーワードマッチし、最初にヒットしたトピックを返す。"""
    title = item.get("title", "")
    body = item.get("body", "")[:300]
    for field in (title, body):
        for topic in topics:
            for pat in _topic_patterns(topic):
                if pat.search(field):
                    return topic
    return None


def _dedup_by_url(items: list[CollectedItem]) -> list[CollectedItem]:
    seen: set[str] = set()
    result: list[CollectedItem] = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            result.append(item)
    return result


def _filter_by_date(items: list[CollectedItem], recency_days: int) -> list[CollectedItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=recency_days)
    result: list[CollectedItem] = []
    for item in items:
        try:
            pub = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                result.append(item)
        except (ValueError, KeyError):
            result.append(item)
    return result


def _score_relevance(item: CollectedItem, topics: list[str], prompt: str) -> float:
    topic_str = ", ".join(topics)
    content = f"Title: {item['title']}\n{item['body'][:500]}"
    try:
        text = chat(
            [{"role": "user", "content": f"{prompt}\n\nTopics: {topic_str}\n\nArticle:\n{content}"}],
            max_tokens=16,
        )
        return float(text)
    except Exception:
        return 0.5


def merge_filter_node(state: CollectState) -> CollectState:
    config = state["config"]
    items = list(state.get("raw_items", []))

    items = _dedup_by_url(items)
    items = _filter_by_date(items, config.recency_days)

    topics = state.get("topics", [])
    scored: list[CollectedItem] = [None] * len(items)  # type: ignore
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(_score_relevance, item, topics, config.relevance_score_prompt): i
            for i, item in enumerate(items)
        }
        for future in as_completed(future_to_idx):
            i = future_to_idx[future]
            score = future.result()
            scored[i] = {**items[i], "relevance_score": score}

    passing = [i for i in scored if i["relevance_score"] >= config.filter_threshold]

    # トピック別クォータ: 各トピックから均等に枠を確保する
    n_topics = max(len(topics), 1)
    slots_per_topic = math.ceil(config.max_items_per_run / n_topics)

    topic_buckets: dict[str, list[CollectedItem]] = {t: [] for t in topics}
    overflow: list[CollectedItem] = []

    for item in passing:
        topic = _assign_topic(item, topics)
        if topic:
            topic_buckets[topic].append(item)
        else:
            overflow.append(item)

    filtered: list[CollectedItem] = []
    for topic in topics:
        bucket = sorted(topic_buckets[topic], key=lambda x: x["relevance_score"], reverse=True)
        filtered.extend(bucket[:slots_per_topic])

    # 余ったスロットをスコア順で埋める
    remaining = config.max_items_per_run - len(filtered)
    if remaining > 0:
        overflow.sort(key=lambda x: x["relevance_score"], reverse=True)
        filtered.extend(overflow[:remaining])

    print(
        f"[merge_filter] raw={len(items)} passing={len(passing)} "
        f"per_topic_slots={slots_per_topic} final={len(filtered)}"
    )
    return {"filtered_items": filtered}
