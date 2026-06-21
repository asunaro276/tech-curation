"""Summarize & Format node: LLM summary, content type classification, template application."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from tech_curation.collect.state import CollectedItem, CollectState
from tech_curation.llm import chat

# LLM が生成する前置き行（「以下は〜」等）を除去するパターン
_PREAMBLE_RE = re.compile(
    r"^(?:(?:以下[はにが]|ご依頼|下記[はに])[^\n]*\n+|---\n+|\n+)+"
)

MAX_WORKERS = 12

VALID_CONTENT_TYPES = {"code", "comparison", "trend"}


def _summarize(item: CollectedItem, prompt: str) -> str:
    content = f"Title: {item['title']}\n\n{item['body'][:1000]}"
    try:
        return chat(
            [{"role": "user", "content": f"{prompt}\n\nArticle:\n{content}"}],
            max_tokens=256,
        )
    except Exception:
        return item["body"][:300]


def _classify(item: CollectedItem, prompt: str) -> str:
    content = f"Title: {item['title']}\n\n{item['body'][:500]}"
    try:
        label = chat(
            [{"role": "user", "content": f"{prompt}\n\nContent:\n{content}"}],
            max_tokens=16,
        ).lower()
        return label if label in VALID_CONTENT_TYPES else "trend"
    except Exception:
        return "trend"


def _clean_summary(text: str) -> str:
    """前置き除去・Markdown ヘッダ太字化・コードブロック補完。"""
    text = _PREAMBLE_RE.sub("", text)
    text = re.sub(r"^#{1,3} (.+)$", r"**\1**", text, flags=re.MULTILINE)
    if text.count("```") % 2 != 0:
        text = text.rstrip() + "\n```"
    return text.strip()


def _process_item(item: CollectedItem, summarize_prompt: str, classify_prompt: str) -> CollectedItem:
    summary = _clean_summary(_summarize(item, summarize_prompt))
    content_type = _classify(item, classify_prompt)
    return {**item, "summary": summary, "content_type": content_type}


def summarize_format_node(state: CollectState) -> CollectState:
    config = state["config"]
    items = list(state.get("filtered_items", []))
    topics = state.get("topics", [])
    topic_str = "、".join(topics) if topics else ""
    summarize_prompt = config.summarize_prompt
    if topic_str:
        summarize_prompt = f"関心トピック: {topic_str}\n\n{summarize_prompt}"

    result: list[CollectedItem] = [None] * len(items)  # type: ignore
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(_process_item, item, summarize_prompt, config.content_type_prompt): i
            for i, item in enumerate(items)
        }
        for future in as_completed(future_to_idx):
            i = future_to_idx[future]
            result[i] = future.result()

    return {"formatted_items": result}
