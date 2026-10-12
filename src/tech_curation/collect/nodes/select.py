"""Select node: Jev judges each article, groups same-subject articles, code keeps the top K groups per topic."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from tech_curation.collect.grouping import group_topic, representative_of
from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.jev import judge_worth_and_primary
from tech_curation.obsidian.records import PastHistory, load_past_history

MAX_WORKERS = 12


def _vault_root() -> Path:
    return Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))


def _load_history(recency_days: int) -> PastHistory:
    today = datetime.now(timezone.utc).date()  # レポートのファイル名と同じく UTC の日付
    return load_past_history(_vault_root(), today, recency_days)


def select_node(state: CollectState) -> CollectState:
    config = state["config"]
    items: list[CollectedItem] = list(state.get("filtered_items", []))
    if not items:
        return {"filtered_items": []}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        judged = list(executor.map(lambda item: judge_worth_and_primary(item, config.worth_criteria), items))
    items = [{**item, "worth": worth, "is_primary": primary} for item, (worth, primary) in zip(items, judged)]

    by_topic: dict[str, list[CollectedItem]] = {}
    for item in items:
        by_topic.setdefault(item.get("topic", "") or "未分類", []).append(item)

    history = _load_history(config.recency_days)

    # グループの状態は前の判定に依存するのでトピック内は逐次、トピック間は並列に処理する
    def process(topic: str) -> list[CollectedItem]:
        groups = group_topic(
            by_topic[topic],
            history["groups_by_topic"].get(topic, []),
            history["urls"],
            config.grouping_criteria,
        )
        reps = sorted((representative_of(g) for g in groups), key=lambda r: r.get("worth", 0.0), reverse=True)
        kept = reps[: config.quota_for(topic)]
        for rep in reps:
            label = "keep" if any(rep is k for k in kept) else "drop"
            print(f"  [{label}] {topic} worth={rep.get('worth', 0.0):.2f} +{len(rep['related'])} {rep['title'][:60]}")
        return kept

    topics = list(by_topic)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process, topics))

    selected = [rep for kept in results for rep in kept]
    n_articles = sum(1 + len(rep["related"]) for rep in selected)
    print(f"[select] {len(items)} articles → {len(selected)} groups ({n_articles} articles)")
    return {"filtered_items": selected}
