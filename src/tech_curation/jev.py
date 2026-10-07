"""Shared Jev client (TypeSafe AI System One model) for typed per-article judgments."""
from __future__ import annotations

import re
from functools import lru_cache

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from tech_curation.collect.state import CollectedItem

NEUTRAL = 0.5
BODY_LIMIT = 1500
CATCHALL_TOPIC = "トレンド"

_RUBRIC_LINE_RE = re.compile(r"^\s*-\s*(?:\d+\s*:\s*)?(.+?)\s*$")


@lru_cache(maxsize=1)
def _client() -> TypeSafeClient:
    # API キーは TYPESAFE_API_KEY から読まれる。httpx2.Client はスレッド間で共有できる
    return TypeSafeClient()


def parse_rubric(text: str) -> list[str]:
    """「- 0: 説明」形式の行を段階の説明リストに変換する（先頭から 0, 1, 2, … の順）。"""
    levels = []
    for line in text.splitlines():
        m = _RUBRIC_LINE_RE.match(line)
        if m:
            levels.append(m.group(1))
    return levels


def normalize_score(score: float, n_levels: int) -> float:
    """期待スコア（0〜n_levels-1）を 0.0〜1.0 に正規化する。"""
    if n_levels < 2:
        return NEUTRAL
    return min(1.0, max(0.0, score / (n_levels - 1)))


def _article_state(item: CollectedItem) -> dict:
    return {
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "topic": item.get("topic", ""),
        "body": (item.get("body", "") or "")[:BODY_LIMIT],
    }


def judge_relevance_and_topic(
    item: CollectedItem,
    topics: list[str],
    relevance_criteria: str,
) -> tuple[float, str | None]:
    """関連度（0〜1）とトピックを1回の呼び出しで判定する。失敗時は (0.5, None)。"""
    rubric = parse_rubric(relevance_criteria)
    specific = [t for t in topics if t != CATCHALL_TOPIC]
    topic_criteria: dict[str, str | None] = {t: None for t in specific}
    topic_criteria[CATCHALL_TOPIC] = "どの個別トピックにも当てはまらない"
    try:
        response = _client().system_one(
            state=_article_state(item),
            questions={
                "relevance": Score(
                    instructions=f"関心トピック（{', '.join(topics)}）に対して、この記事はどれだけ関連しているか",
                    criteria=rubric,
                ),
                "topic": Choice(
                    instructions="この記事が最も強く扱っているトピックはどれか",
                    criteria=topic_criteria,
                ),
            },
        )
        relevance = normalize_score(response.scores["relevance"].score, len(rubric))
        topic = response.choices["topic"].choice
        print(f"[jev] relevance={relevance:.2f} topic={topic} | {item['title'][:60]}")
        return relevance, topic
    except Exception as exc:
        print(f"[jev] ERR({exc}) | {item['title'][:60]}")
        return NEUTRAL, None


def judge_worth(item: CollectedItem, worth_criteria: str) -> float:
    """「要約する価値があるか」の確率を返す。失敗時は 0.5。"""
    try:
        response = _client().system_one(
            state=_article_state(item),
            questions={"worth": Noul(instructions=worth_criteria)},
        )
        return response.nouls["worth"].noul
    except Exception as exc:
        print(f"[jev] ERR({exc}) | {item['title'][:60]}")
        return NEUTRAL
