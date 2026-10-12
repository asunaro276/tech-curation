"""Greedy topic grouping: merges same-subject articles and checks them against past reports."""
from __future__ import annotations

import re
from typing import TypedDict

from tech_curation.collect.state import CollectedItem, FollowRef
from tech_curation.jev import NEW_GROUP, judge_group, judge_same_subject
from tech_curation.obsidian.records import PastGroup

_KANA_RE = re.compile(r"[぀-ヿ]")


class Group(TypedDict):
    members: list[CollectedItem]   # 先頭がグループの核（最初に入った記事）
    follow_of: FollowRef | None


def is_japanese(item: CollectedItem) -> bool:
    """タイトルか本文の冒頭に平仮名・片仮名が含まれれば日本語とみなす。"""
    text = item.get("title", "") + (item.get("body", "") or "")[:200]
    return bool(_KANA_RE.search(text))


def is_primary(item: CollectedItem) -> bool:
    # GitHub 由来（リポジトリ・リリース）は作者本人による一次情報として扱う
    return item.get("source", "") == "github" or item.get("is_primary", 0.0) >= 0.5


def group_topic(
    items: list[CollectedItem],
    past_groups: list[PastGroup],
    past_urls: set[str],
    grouping_criteria: str,
) -> list[Group]:
    """1トピック分の記事を worth の降順に1本ずつ処理し、貪欲法でグループに分ける。"""
    groups: list[Group] = []
    for item in sorted(items, key=lambda x: x.get("worth", 0.0), reverse=True):
        title = item["title"][:60]
        if item["url"] in past_urls:
            print(f"  [group] drop (reported URL) {title}")
            continue
        if not groups and not past_groups:
            groups.append(Group(members=[item], follow_of=None))
            continue

        judged = judge_group(item, [g["members"][0] for g in groups], past_groups, grouping_criteria)
        label, conf = judged if judged else (NEW_GROUP, 0.0)

        if label.startswith("g"):
            seed = groups[int(label[1:])]["members"][0]
            if _confirmed(item, seed, grouping_criteria, f"{label} conf={conf:.2f}"):
                groups[int(label[1:])]["members"].append(item)
                print(f"  [group] join {label} conf={conf:.2f} {title} ← {seed['title'][:40]}")
                continue
        elif label.startswith("same:p"):
            past = past_groups[int(label.split(":p")[1])]
            if _confirmed(item, _past_as_item(past), grouping_criteria, f"{label} conf={conf:.2f}"):
                print(f"  [group] drop (same as {past['date']} #{past['no']} conf={conf:.2f}) {title} ← {past['title'][:40]}")
                continue
        elif label.startswith("follow:p"):
            past = past_groups[int(label.split(":p")[1])]
            groups.append(Group(
                members=[item],
                follow_of=FollowRef(date=past["date"], no=past["no"], title=past["title"]),
            ))
            print(f"  [group] follow-up of {past['date']} #{past['no']} conf={conf:.2f} {title} ← {past['title'][:40]}")
            continue

        # new、判定の失敗、1対1の確認で否定された場合は新しいグループにする
        groups.append(Group(members=[item], follow_of=None))
        print(f"  [group] new g{len(groups) - 1} {title}")
    return groups


def _past_as_item(past: PastGroup) -> CollectedItem:
    return {"title": past["title"], "body": past.get("summary", ""), "source": "", "topic": past.get("topic", "")}


def _confirmed(item: CollectedItem, other: CollectedItem, grouping_criteria: str, context: str) -> bool:
    """Choice の結果を1対1の判定で確かめる。確認できなければ（失敗も含めて）まとめない。"""
    same = judge_same_subject(item, other, grouping_criteria)
    if same is not None and same >= 0.5:
        return True
    shown = "ERR" if same is None else f"{same:.2f}"
    print(f"  [group] reject {context} same={shown} {item['title'][:60]} ← {other['title'][:40]}")
    return False


def representative_of(group: Group) -> CollectedItem:
    """一次情報 > 日本語 > worth の順で代表を選び、残りを related として持たせる。"""
    members = group["members"]
    rep = max(members, key=lambda x: (is_primary(x), is_japanese(x), x.get("worth", 0.0)))
    related = [m for m in members if m is not rep]
    return {**rep, "related": related, "follow_of": group["follow_of"]}
