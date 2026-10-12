"""Select node: Jev judges interest / release per article, releases are grouped, code keeps the top K per topic."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from tech_curation.collect.grouping import group_candidates, representative_of
from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.jev import judge_selection
from tech_curation.obsidian.records import PastHistory, load_past_history

MAX_WORKERS = 12


def _vault_root() -> Path:
    return Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))


POLICY_PATH = "agent-config/policy.md"


def _load_policy() -> str:
    """ユーザーの普段の好み（policy.md）。興味の判定に添える。"""
    path = _vault_root() / POLICY_PATH
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _load_history(recency_days: int) -> PastHistory:
    today = datetime.now(timezone.utc).date()  # レポートのファイル名と同じく UTC の日付
    return load_past_history(_vault_root(), today, recency_days)


def select_node(state: CollectState) -> CollectState:
    config = state["config"]
    items: list[CollectedItem] = list(state.get("filtered_items", []))
    if not items:
        return {"filtered_items": []}

    policy = _load_policy()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        judged = list(executor.map(lambda item: judge_selection(item, config.worth_criteria, policy), items))
    items = [
        {**item, "worth": j.worth, "is_release": j.is_release, "is_primary": j.is_primary}
        for item, j in zip(items, judged)
    ]

    by_topic: dict[str, list[CollectedItem]] = {}
    for item in items:
        by_topic.setdefault(item.get("topic", "") or "未分類", []).append(item)

    history = _load_history(config.recency_days)

    # グループの状態は前の判定に依存するのでトピック内は逐次、トピック間は並列に処理する
    def process(topic: str) -> list[CollectedItem]:
        groups = group_candidates(
            by_topic[topic],
            history["groups_by_topic"].get(topic, []),
            history["urls"],
            config.grouping_criteria,
        )
        reps = sorted((representative_of(g) for g in groups), key=lambda r: r.get("worth", 0.0), reverse=True)
        kept = reps[: config.quota_for(topic)]
        for rep in reps:
            label = "keep" if any(rep is k for k in kept) else "drop"
            kind = "release" if rep.get("is_release", 0.0) >= 0.5 else "trend"
            print(
                f"  [{label}] {topic} {kind} worth={rep.get('worth', 0.0):.2f} primary={rep.get('is_primary', 0.0):.2f}"
                f" +{len(rep['related'])} {rep['title'][:60]}"
            )
        return kept

    topics = list(by_topic)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process, topics))

    selected = [rep for kept in results for rep in kept]
    n_articles = sum(1 + len(rep["related"]) for rep in selected)
    print(f"[select] {len(items)} articles → {len(selected)} groups ({n_articles} articles)")
    return {"filtered_items": selected}
