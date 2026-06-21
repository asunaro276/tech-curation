"""Review node: LLM checks each item for quality issues and flags them."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tech_curation.collect.state import CollectState, ReviewIssue
from tech_curation.llm import chat, MODEL_SMART

MAX_ITERATIONS = 3

REVIEW_VAULT_PATH = "agent-config/review.md"

_SYSTEM_HEADER = "あなたは技術キュレーションのレビュアーです。\n記事リストを精査して品質の低い記事を特定してください。\n\n"
_SYSTEM_FOOTER = """
**絶対に除去してはならない記事**: カテゴリが「トレンド」の記事は、技術的な内容であれば理由に関わらず除去禁止。ZennやQiitaのトレンドフィードから取得した価値ある記事として意図的に含めている。

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

_SYSTEM_DEFAULT_CRITERIA = """\
以下の基準で問題のある記事を見つけてください：
- マーケティング・PR色が強い（製品宣伝、「〜を使えば解決」系）
- 自作ツールや個人プロダクトの宣伝（著名OSSでないもの）
- いずれのトピックとも明らかに無関係
- 要約が日本語でない、または意味をなさない内容
- コードブロックが閉じられていない、または閉じる位置が間違っている（``` が偶数個でない場合）
- 「カテゴリ」に記載のトピックと内容が明らかに一致しない

以下は除去してはいけません：
- 収集対象トピックに関連するOSSライブラリ・ツールのリリースや更新情報
- トピックに関する技術的な解説・比較・事例記事
- GitHub上の有名・活発なリポジトリ
"""


def _load_review_criteria() -> str:
    vault_root = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
    review_path = vault_root / REVIEW_VAULT_PATH
    if review_path.exists():
        return review_path.read_text(encoding="utf-8")
    return _SYSTEM_DEFAULT_CRITERIA


def review_node(state: CollectState) -> CollectState:
    items = state.get("formatted_items", [])
    topics = state.get("topics", [])
    iterations = state.get("review_iterations", 0)

    if not items:
        return {"review_issues": [], "review_iterations": iterations}

    topic_str = "、".join(topics)
    items_text = "\n\n".join(
        f"[{i}] タイトル: {item['title']}\nカテゴリ: {item.get('topic', '未分類')}\nソース: {item['source']}\n要約: {item['summary']}"
        for i, item in enumerate(items)
    )
    prompt = f"収集対象トピック: {topic_str}\n\n記事リスト:\n{items_text}"

    criteria = _load_review_criteria()
    system = _SYSTEM_HEADER + criteria + _SYSTEM_FOOTER

    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            system=system,
            max_tokens=4096,
            model=MODEL_SMART,
        )
        # JSON配列を抽出（前置テキストや```ブロックを除去）
        raw = raw.strip()
        bracket_idx = raw.find("[")
        if bracket_idx != -1:
            raw = raw[bracket_idx:]
        # 末尾の ``` を除去
        if "```" in raw:
            raw = raw[:raw.rfind("```")]
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
