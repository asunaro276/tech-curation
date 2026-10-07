"""Daily group records (tech-curation/YYYY-MM-DD/items.json) for cross-day dedup and feedback lookup."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict

from tech_curation.collect.state import CollectedItem

RECORD_FILENAME = "items.json"


class PastGroup(TypedDict):
    date: str
    no: int
    topic: str
    title: str
    summary: str


class PastHistory(TypedDict):
    groups_by_topic: dict[str, list[PastGroup]]  # 新しい日付順
    urls: set[str]


def record_path(date_str: str) -> str:
    return f"tech-curation/{date_str}/{RECORD_FILENAME}"


def _article_entry(item: CollectedItem) -> dict:
    return {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "primary": item.get("is_primary", 0.0) >= 0.5,
    }


def build_daily_record(date_str: str, numbered: list[tuple[int, str, CollectedItem]]) -> dict:
    """レポートと同じ通し番号でグループの記録を作る。numbered は (no, topic, 代表記事) のリスト。"""
    groups = []
    for no, topic, item in numbered:
        groups.append({
            "no": no,
            "topic": topic,
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "follow_of": item.get("follow_of"),
            "articles": [_article_entry(item)] + [_article_entry(r) for r in item.get("related", [])],
        })
    return {"date": date_str, "groups": groups}


def read_record(vault_root: Path, date_str: str) -> dict | None:
    path = vault_root / record_path(date_str)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        if path.exists():
            print(f"[records] skip broken {path}: {exc}")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        print(f"[records] skip malformed {path}")
        return None
    return data


def load_past_history(vault_root: Path, today: date, days: int) -> PastHistory:
    """今日を除く過去 days 日分の記録を読む。欠けている日・壊れたファイルは飛ばす。"""
    groups_by_topic: dict[str, list[PastGroup]] = {}
    urls: set[str] = set()
    for offset in range(1, days + 1):
        date_str = (today - timedelta(days=offset)).isoformat()
        record = read_record(vault_root, date_str)
        if record is None:
            continue
        for group in record["groups"]:
            if not isinstance(group, dict):
                continue
            topic = group.get("topic", "")
            groups_by_topic.setdefault(topic, []).append(PastGroup(
                date=date_str,
                no=int(group.get("no", 0)),
                topic=topic,
                title=group.get("title", ""),
                summary=group.get("summary", ""),
            ))
            for article in group.get("articles", []):
                if isinstance(article, dict) and article.get("url"):
                    urls.add(article["url"])
    return PastHistory(groups_by_topic=groups_by_topic, urls=urls)
