"""Select node: LLM decides which fetched articles are worth summarizing."""
from __future__ import annotations

import json

from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.llm import chat

_PROMPT = """\
あなたは技術キュレーターです。
収集した記事の中から、読者にとって要約する価値がある記事を選んでください。

## 選ぶ基準
- 具体的な技術変更・新機能・実装例がある
- リリースノートや breaking change 情報
- 独自の洞察・比較・検証記事
- 実際のコードやベンチマークを含む

## 除外する基準（本当に問題がある場合のみ除外）
- 内容がほぼ空・タイトルと本文が全く一致しない
- 全く同一の話題の重複記事が複数ある場合は1本だけ残す

## トピック別の選ぶ本数（これを厳守すること）
- Go: 1 本（最も価値ある1本だけ選ぶ）
- TypeScript/JavaScript: 1〜2 本
- Ruby: 1〜2 本
- Ruby on Rails: 1〜2 本
- Claude: 2〜3 本
- vue: 1〜2 本
- postgresql: 2〜3 本
- トレンド: 3〜5 本（できるだけ多く選ぶ）

選んだ記事のインデックス番号だけを JSON 配列で返してください。例: [0, 2, 5, 7]
前置きや説明文は不要です。JSON のみ返してください。
"""


def select_node(state: CollectState) -> CollectState:
    items: list[CollectedItem] = list(state.get("filtered_items", []))
    if not items:
        return {"filtered_items": []}

    items_text = "\n\n".join(
        f"[{i}] トピック: {item.get('topic', '未分類')} | ソース: {item.get('source', '')}\n"
        f"タイトル: {item['title']}\n"
        f"内容: {(item.get('body', '') or '')[:400]}"
        for i, item in enumerate(items)
    )

    try:
        raw = chat(
            [{"role": "user", "content": f"{_PROMPT}\n\n## 記事一覧\n\n{items_text}"}],
            max_tokens=256,
        ).strip()

        bracket_idx = raw.find("[")
        if bracket_idx != -1:
            raw = raw[bracket_idx:]
            close_idx = raw.rfind("]")
            if close_idx != -1:
                raw = raw[: close_idx + 1]

        selected_indices_raw: list[int] = json.loads(raw)
        kept: set[int] = {i for i in selected_indices_raw if 0 <= i < len(items)}

        # 各トピックから最低1本をコードで保証
        topic_to_indices: dict[str, list[int]] = {}
        for i, item in enumerate(items):
            t = item.get("topic", "") or "未分類"
            topic_to_indices.setdefault(t, []).append(i)

        for t, idxs in topic_to_indices.items():
            if not any(i in kept for i in idxs):
                # LLMが全削除したトピックは最高スコアの1本を強制追加
                best = max(idxs, key=lambda i: items[i].get("relevance_score", 0.0))
                kept.add(best)
                print(f"  [force-keep] [{best}] {items[best]['title'][:60]} (topic={t})")

        selected = [items[i] for i in sorted(kept)]

        for i, item in enumerate(items):
            label = "keep" if i in kept else "drop"
            print(f"  [{label}] [{i}] {item['title'][:60]}")
        print(f"[select] {len(items)} → {len(selected)} articles selected for summarization")

        return {"filtered_items": selected}
    except Exception as exc:
        print(f"[select] ERR({exc}) — using all {len(items)} items")
        return {"filtered_items": items}
