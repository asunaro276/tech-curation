"""Merge & Filter node: dedup, date filter, and LLM relevance scoring."""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.llm import chat

MAX_WORKERS = 12

# トレンド記事として重視するソースへのスコアブースト
_SOURCE_BOOST: dict[str, float] = {
    "zenn": 0.25,
    "qiita": 0.25,
    "jser": 0.30,
}

# トピック名だけでは拾えない別名・略称
_TOPIC_EXTRAS: dict[str, list[str]] = {
    "typescript/javascript": ["typescript", "javascript", "tsc", "tsx", "jser", "js"],
    "go": ["golang"],
    "ruby on rails": ["rails"],
    "vue": ["vue.js", "vuejs", "nuxt", "pinia"],
    "postgresql": ["postgres"],
    "claude": ["anthropic"],
    "node.js": ["nodejs", "node"],
    "react": ["react.js", "reactjs", "next.js", "nextjs"],
}


def _topic_patterns(topic: str) -> list[re.Pattern]:
    keywords = [topic.lower()] + _TOPIC_EXTRAS.get(topic.lower(), [])
    return [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]


_CATCHALL_TOPIC = "トレンド"


def _assign_topic(item: CollectedItem, topics: list[str]) -> str | None:
    """タイトル→本文の順でキーワードマッチし、最初にヒットしたトピックを返す。
    キーワード不一致の場合は RSS の feed topic_hint を使用。
    トレンドはキーワードマッチせず、他のどのトピックにも合致しなかった記事の catch-all として機能する。"""
    title = item.get("title", "")
    body = item.get("body", "")[:600]
    specific = [t for t in topics if t != _CATCHALL_TOPIC]
    for field in (title, body):
        for topic in specific:
            for pat in _topic_patterns(topic):
                if pat.search(field):
                    return topic
    # キーワード不一致: RSS フィードの topic_hint を利用（フィード専用チャンネル記事）
    hint = item.get("topic", "")
    if hint and hint in topics and hint != _CATCHALL_TOPIC:
        return hint
    if _CATCHALL_TOPIC in topics:
        return _CATCHALL_TOPIC
    return None


# 日次ランキング・集約ページのパターン（個別記事の重複になるため除外）
_DIGEST_RE = re.compile(r"^【\d+月\d+日ランキング】")


def _is_digest(item: CollectedItem) -> bool:
    title = item.get("title", "")
    return bool(_DIGEST_RE.match(title))


def _dedup_by_url(items: list[CollectedItem]) -> list[CollectedItem]:
    seen: set[str] = set()
    result: list[CollectedItem] = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            result.append(item)
    return result


def _dedup_by_title(items: list[CollectedItem]) -> list[CollectedItem]:
    """タイトル先頭80文字で正規化してほぼ同じ記事を除去する。
    topic ヒント付きアイテムを優先し、同条件なら URL が短い方（個別記事）を残す。"""
    seen: dict[str, CollectedItem] = {}
    for item in items:
        key = item.get("title", "")[:80].lower().strip()
        if not key:
            continue
        if key not in seen:
            seen[key] = item
        else:
            existing = seen[key]
            new_has_topic = bool(item.get("topic", ""))
            old_has_topic = bool(existing.get("topic", ""))
            # topic 付きを優先。同条件なら URL が短い方
            if new_has_topic and not old_has_topic:
                seen[key] = item
            elif not new_has_topic and old_has_topic:
                pass
            elif len(item["url"]) < len(existing["url"]):
                seen[key] = item
    return list(seen.values())


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
        ).strip()
        score = float(text)
        print(f"[score] {score:.2f} | {item['title'][:60]}")
        return score
    except Exception as exc:
        print(f"[score] ERR({exc}) | {item['title'][:60]}")
        return 0.5


def merge_filter_node(state: CollectState) -> CollectState:
    config = state["config"]
    items = list(state.get("raw_items", []))

    items = _dedup_by_url(items)
    items = [i for i in items if not _is_digest(i)]  # 日次ランキング集約を除外
    items = _dedup_by_title(items)                    # タイトル類似による重複除去
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
            boost = _SOURCE_BOOST.get(items[i].get("source", ""), 0.0)
            score = min(1.0, score + boost)
            # フィードURLヒントがあればそれを優先し、なければキーワードマッチ
            pre_topic = items[i].get("topic", "")
            assigned = pre_topic if (pre_topic and pre_topic in topics) else (_assign_topic(items[i], topics) or "")
            scored[i] = {**items[i], "relevance_score": score, "topic": assigned}

    passing = [i for i in scored if i["relevance_score"] >= config.filter_threshold]

    # トピック別クォータ: 各トピックから均等に枠を確保する
    n_topics = max(len(topics), 1)
    slots_per_topic = math.ceil(config.max_items_per_run / n_topics)

    topic_buckets: dict[str, list[CollectedItem]] = {t: [] for t in topics}

    TREND_TOPIC = "トレンド"
    for item in passing:
        topic = item.get("topic", "")
        if topic and topic in topic_buckets and topic != TREND_TOPIC:
            topic_buckets[topic].append(item)
        elif TREND_TOPIC in topic_buckets:
            # Zenn・Qiita トレンド記事のみトレンドバケットへ（GitHub リポジトリは除外）
            if (not topic or topic == TREND_TOPIC) and item.get("source", "") in ("zenn", "qiita", "codezine"):
                topic_buckets[TREND_TOPIC].append({**item, "topic": TREND_TOPIC})

    filtered: list[CollectedItem] = []
    for topic in topics:
        bucket = sorted(topic_buckets[topic], key=lambda x: x["relevance_score"], reverse=True)
        filtered.extend(bucket[:slots_per_topic])

    bucket_summary = {t: len(topic_buckets[t]) for t in topics}
    print(
        f"[merge_filter] raw={len(items)} passing={len(passing)} "
        f"per_topic_slots={slots_per_topic} final={len(filtered)} "
        f"buckets={bucket_summary}"
    )
    return {"filtered_items": filtered}
