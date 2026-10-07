"""Select node: Jev judges each article's worth, code keeps the top K per topic."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.jev import judge_worth

MAX_WORKERS = 12


def select_node(state: CollectState) -> CollectState:
    config = state["config"]
    items: list[CollectedItem] = list(state.get("filtered_items", []))
    if not items:
        return {"filtered_items": []}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        worths = list(executor.map(lambda item: judge_worth(item, config.worth_criteria), items))

    # トピックごとに worth の降順で並べ、上位 K 本を残す（K >= 1 なので各トピック最低1本は残る）
    topic_to_indices: dict[str, list[int]] = {}
    for i, item in enumerate(items):
        topic_to_indices.setdefault(item.get("topic", "") or "未分類", []).append(i)

    kept: set[int] = set()
    for topic, idxs in topic_to_indices.items():
        ranked = sorted(idxs, key=lambda i: worths[i], reverse=True)
        kept.update(ranked[: config.quota_for(topic)])

    for i, item in enumerate(items):
        label = "keep" if i in kept else "drop"
        print(f"  [{label}] [{i}] worth={worths[i]:.2f} {item['title'][:60]}")

    selected = [items[i] for i in sorted(kept)]
    print(f"[select] {len(items)} → {len(selected)} articles selected for summarization")
    return {"filtered_items": selected}
