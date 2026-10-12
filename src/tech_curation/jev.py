"""Shared Jev client (TypeSafe AI System One model) for typed per-article judgments."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import NamedTuple

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


class Selection(NamedTuple):
    worth: float       # このユーザーが興味を持ちそうか
    is_release: float  # 特定のソフトウェアのリリース・新機能・公式発表を扱う記事か
    is_primary: float  # 公式の一次情報か


def judge_selection(item: CollectedItem, worth_criteria: str, policy: str = "") -> Selection:
    """興味・リリース情報か・一次情報かを1回の呼び出しで判定する。失敗時はすべて 0.5。"""
    interest = worth_criteria if not policy else f"{worth_criteria}\n\nこのユーザーの普段の好み:\n{policy}"
    try:
        response = _client().system_one(
            state=_article_state(item),
            questions={
                "worth": Noul(instructions=interest),
                "is_release": Noul(
                    instructions=(
                        "この記事は、特定のソフトウェア・サービスのリリース情報か。新バージョン・新機能・"
                        "非推奨化・公式の発表を扱う記事なら yes（公式のリリースノートでも、第三者による解説・まとめでもよい）。"
                        "設計・実装の解説、体験記、エッセイ、入門記事は no。"
                    ),
                ),
                "is_primary": Noul(
                    instructions=(
                        "この記事は公式の一次情報か。プロジェクト・企業・標準化団体の公式ドキュメント、"
                        "公式ブログ、リリースノート、公式アナウンスなら yes。"
                        "個人や第三者による解説記事・体験記・検証記事・まとめ記事は、技術的に正確でも no。"
                    ),
                ),
            },
        )
        nouls = response.nouls
        return Selection(nouls["worth"].noul, nouls["is_release"].noul, nouls["is_primary"].noul)
    except Exception as exc:
        print(f"[jev] ERR({exc}) | {item['title'][:60]}")
        return Selection(NEUTRAL, NEUTRAL, NEUTRAL)


MAX_CHOICE_LABELS = 255
NEW_GROUP = "new"


def build_group_choices(
    today_seeds: list[CollectedItem],
    past_groups: list[dict],
) -> dict[str, dict | str]:
    """グループ判定の選択肢を作る。new / gN（今日のグループ）/ same:pK・follow:pK（過去のグループ）。

    過去のグループは新しい順に渡し、Choice のラベル上限に収まる分だけ使う。
    """
    choices: dict[str, dict | str] = {NEW_GROUP: "今日・過去のどのリリースとも異なる新しいリリース・発表"}
    for i, seed in enumerate(today_seeds):
        choices[f"g{i}"] = {
            "relation": "今日の別の記事と同じリリース・発表",
            "title": seed.get("title", ""),
            "excerpt": (seed.get("body", "") or "")[:200],
        }
    max_past = max(0, (MAX_CHOICE_LABELS - len(choices)) // 2)
    for j, past in enumerate(past_groups[:max_past]):
        base = {"date": past["date"], "title": past["title"], "summary": (past.get("summary", "") or "")[:200]}
        choices[f"same:p{j}"] = {"relation": "過去に掲載したリリースと同じ（新しい情報はない）", **base}
        choices[f"follow:p{j}"] = {"relation": "過去に掲載したリリースの続報（RC から正式版、パッチ版、追加の発表）", **base}
    return choices


def judge_group(
    item: CollectedItem,
    today_seeds: list[CollectedItem],
    past_groups: list[dict],
    grouping_criteria: str,
) -> tuple[str, float] | None:
    """記事がどのグループに属するかのラベルと確信度を返す。失敗時は None。"""
    choices = build_group_choices(today_seeds, past_groups)
    try:
        response = _client().system_one(
            state=_article_state(item),
            questions={"group": Choice(instructions=grouping_criteria, criteria=choices)},
        )
        answer = response.choices["group"]
        if answer.choice not in choices:
            raise ValueError(f"unknown label {answer.choice!r}")
        return answer.choice, answer.confidence
    except Exception as exc:
        print(f"[jev] group ERR({exc}) | {item['title'][:60]}")
        return None


def judge_same_subject(item: CollectedItem, other: CollectedItem, grouping_criteria: str) -> float | None:
    """2本の記事が同じリリース・発表を扱っている確率を返す。失敗時は None。

    Choice は選択肢のどれかを選ぶ形なので、ふさわしいグループがないときに手近なグループを選ぶことがある。
    既存のグループに入れる前にこの1対1の判定で確かめる。
    """
    try:
        response = _client().system_one(
            state={"article_a": _article_state(item), "article_b": _article_state(other)},
            questions={
                "same": Noul(
                    instructions=(
                        f"{grouping_criteria}\n\n"
                        "記事 A と記事 B は同じリリース・発表を扱っているか。"
                        "同じソフトウェアの同じバージョン・同じ発表なら yes。"
                        "同じソフトウェアでも別のバージョンや別の発表、テーマが近いだけなら no。"
                    ),
                ),
            },
        )
        return response.nouls["same"].noul
    except Exception as exc:
        print(f"[jev] same ERR({exc}) | {item['title'][:60]}")
        return None
