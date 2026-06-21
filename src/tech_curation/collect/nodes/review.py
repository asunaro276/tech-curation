"""Review node: LLM checks each item for quality issues and flags them."""
from __future__ import annotations

import json

from tech_curation.collect.state import CollectState, ReviewIssue
from tech_curation.llm import chat, MODEL_SMART

MAX_ITERATIONS = 3

_SYSTEM = """\
あなたは技術キュレーションのレビュアーです。
記事リストを精査して品質の低い記事を特定してください。

以下の基準で問題のある記事を見つけてください：
- マーケティング・PR色が強い（製品宣伝、「〜を使えば解決」系）
- 自作ツールや個人プロダクトの宣伝（著名OSSでないもの）
- いずれのトピックとも明らかに無関係
- 要約が日本語でない、または意味をなさない内容

以下は除去してはいけません：
- 収集対象トピックに関連するOSSライブラリ・ツールのリリースや更新情報
- トピックに関する技術的な解説・比較・事例記事
- GitHub上の有名・活発なリポジトリ

問題がある記事だけJSONの配列で出力してください。問題なければ空配列 [] を返してください。

スキーマ:
[
  {
    "item_index": 0,
    "action": "remove" | "rewrite",
    "reason": "問題の説明（日本語）",
    "rewrite_hint": "rewriteの場合、どう書き直すかのヒント。removeなら空文字"
  }
]

removeは明らかに不要な記事。rewriteは内容は良いが要約の書き方に問題がある場合。
"""


def review_node(state: CollectState) -> CollectState:
    items = state.get("formatted_items", [])
    topics = state.get("topics", [])
    iterations = state.get("review_iterations", 0)

    if not items:
        return {"review_issues": [], "review_iterations": iterations}

    topic_str = "、".join(topics)
    items_text = "\n\n".join(
        f"[{i}] タイトル: {item['title']}\nソース: {item['source']}\n要約: {item['summary']}"
        for i, item in enumerate(items)
    )
    prompt = f"収集対象トピック: {topic_str}\n\n記事リスト:\n{items_text}"

    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            system=_SYSTEM,
            max_tokens=1024,
            model=MODEL_SMART,
        )
        # JSON配列を抽出（```json ... ``` でラップされる場合も考慮）
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        issues_raw = json.loads(raw)
        issues: list[ReviewIssue] = [
            ReviewIssue(
                item_index=int(r["item_index"]),
                action=r.get("action", "remove"),
                reason=r.get("reason", ""),
                rewrite_hint=r.get("rewrite_hint", ""),
            )
            for r in issues_raw
            if isinstance(r, dict) and "item_index" in r
        ]
    except Exception as exc:
        print(f"[review] parse error: {exc}, raw={raw!r:.200}")
        issues = []

    print(f"[review] iter={iterations + 1}, issues={len(issues)}")
    return {"review_issues": issues, "review_iterations": iterations + 1}


def should_revise(state: CollectState) -> str:
    issues = state.get("review_issues", [])
    iterations = state.get("review_iterations", 0)
    if issues and iterations < MAX_ITERATIONS:
        return "revise"
    return "end"
