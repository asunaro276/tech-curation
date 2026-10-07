"""Loads agent configuration from vault/agent-config/prompts.md."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    source_weights: dict[str, float] = field(
        default_factory=lambda: {
            "github": 0.8,
            "rss": 0.6,
            "hackernews": 0.5,
            "substack": 0.4,
        }
    )
    filter_threshold: float = 0.5
    recency_days: int = 7
    max_items_per_run: int = 30
    query_gen_prompt: str = (
        "Generate 3 concise search queries for the topic. "
        "Output as a JSON array of strings."
    )
    relevance_score_prompt: str = (
        "Score the relevance of this item to the given topics on a scale 0.0–1.0. "
        "Return only a JSON number."
    )
    summarize_prompt: str = (
        "Summarize this article in 2–3 sentences focusing on key technical insights. "
        "Return only the summary text."
    )
    content_type_prompt: str = (
        "Classify this content as one of: code, comparison, trend. "
        "Return only the word."
    )
    # Jev に渡す判定基準。relevance_criteria は「- 0: 説明」形式の段階リスト
    relevance_criteria: str = (
        "- 0: 関心トピックと無関係\n"
        "- 1: トピックの名前が出てくるだけで、技術的な内容はほとんどない\n"
        "- 2: トピックに関係する技術内容を一部含む\n"
        "- 3: トピックの技術内容が主題になっている\n"
        "- 4: トピックの中心的な技術内容（新機能・リリース・実装・検証）を具体的に扱っている"
    )
    worth_criteria: str = (
        "この記事は、技術者が要約を読む価値があるか。"
        "具体的な技術変更・新機能・実装例・リリースノート・breaking change・独自の比較や検証・"
        "コードやベンチマークを含む記事は yes。"
        "内容がほぼ空、タイトルと本文が一致しない、宣伝だけの記事は no。"
    )
    topic_quotas: dict[str, int] = field(
        default_factory=lambda: {
            "Go": 1,
            "TypeScript/JavaScript": 2,
            "Ruby": 2,
            "Ruby on Rails": 2,
            "Claude": 3,
            "vue": 2,
            "postgresql": 3,
            "トレンド": 5,
        }
    )
    default_topic_quota: int = 2

    def quota_for(self, topic: str) -> int:
        """トピックの上限本数（大文字小文字を区別しない）。最低 1。"""
        for name, quota in self.topic_quotas.items():
            if name.lower() == topic.lower():
                return max(1, quota)
        return max(1, self.default_topic_quota)


_WEIGHT_RE = re.compile(r"^\s*-\s*(\w+):\s*([0-9.]+)", re.MULTILINE)
_SCALAR_RE = {
    "filter_threshold": re.compile(r"filter_threshold:\s*([0-9.]+)"),
    "recency_days": re.compile(r"recency_days:\s*(\d+)"),
    "max_items_per_run": re.compile(r"max_items_per_run:\s*(\d+)"),
}
_PROMPT_RE = {
    "query_gen_prompt": re.compile(
        r"## query_gen_prompt\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
    "relevance_score_prompt": re.compile(
        r"## relevance_score_prompt\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
    "summarize_prompt": re.compile(
        r"## summarize_prompt\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
    "content_type_prompt": re.compile(
        r"## content_type_prompt\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
    "relevance_criteria": re.compile(
        r"## relevance_criteria\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
    "worth_criteria": re.compile(
        r"## worth_criteria\n(.*?)(?=\n## |\Z)", re.DOTALL
    ),
}
_QUOTA_RE = re.compile(r"^\s*-\s*(.+?):\s*(\d+)\s*$", re.MULTILINE)


def load_config(prompts_path: str | Path) -> AgentConfig:
    text = Path(prompts_path).read_text(encoding="utf-8")
    cfg = AgentConfig()

    weights_section = re.search(
        r"## source_weights\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if weights_section:
        for m in _WEIGHT_RE.finditer(weights_section.group(1)):
            cfg.source_weights[m.group(1)] = float(m.group(2))

    for attr, pattern in _SCALAR_RE.items():
        m = pattern.search(text)
        if m:
            val = m.group(1)
            setattr(cfg, attr, float(val) if "." in val else int(val))

    for attr, pattern in _PROMPT_RE.items():
        m = pattern.search(text)
        if m:
            setattr(cfg, attr, m.group(1).strip())

    quota_section = re.search(r"## topic_quotas\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if quota_section:
        for m in _QUOTA_RE.finditer(quota_section.group(1)):
            name, quota = m.group(1).strip(), int(m.group(2))
            if name == "default":
                cfg.default_topic_quota = quota
            else:
                cfg.topic_quotas[name] = quota

    return cfg


def _default_prompts_md() -> str:
    cfg = AgentConfig()
    weights = "\n".join(f"  - {k}: {v}" for k, v in cfg.source_weights.items())
    quotas = "\n".join(f"- {k}: {v}" for k, v in cfg.topic_quotas.items())
    return (
        f"## source_weights\n{weights}\n\n"
        f"filter_threshold: {cfg.filter_threshold}\n"
        f"recency_days: {cfg.recency_days}\n"
        f"max_items_per_run: {cfg.max_items_per_run}\n\n"
        f"## query_gen_prompt\n{cfg.query_gen_prompt}\n\n"
        f"## relevance_score_prompt\n{cfg.relevance_score_prompt}\n\n"
        f"## summarize_prompt\n{cfg.summarize_prompt}\n\n"
        f"## content_type_prompt\n{cfg.content_type_prompt}\n\n"
        f"## relevance_criteria\n{cfg.relevance_criteria}\n\n"
        f"## worth_criteria\n{cfg.worth_criteria}\n\n"
        f"## topic_quotas\n{quotas}\n- default: {cfg.default_topic_quota}\n"
    )


def _insert_section(text: str, section: str) -> str:
    """改善履歴セクションの直前（なければ末尾）にセクションを追加する。"""
    idx = text.find("## 改善履歴")
    if idx == -1:
        return text.rstrip("\n") + "\n\n" + section
    return text[:idx] + section + "\n" + text[idx:]


def _set_topic_quota(text: str, topic: str, quota: int) -> str:
    quota = max(1, quota)
    section_m = re.search(r"## topic_quotas\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not section_m:
        return _insert_section(text, f"## topic_quotas\n\n- {topic}: {quota}\n")
    body = section_m.group(1)
    line_re = re.compile(rf"^(\s*-\s*){re.escape(topic)}(:\s*)\d+\s*$", re.MULTILINE | re.IGNORECASE)
    if line_re.search(body):
        body = line_re.sub(lambda m: f"{m.group(1)}{topic}{m.group(2)}{quota}", body, count=1)
    else:
        body = body.rstrip("\n") + f"\n- {topic}: {quota}\n"
    return text[: section_m.start(1)] + body + text[section_m.end(1):]


def update_config(
    prompts_path: str | Path,
    param_changes: dict[str, float | int | str] | None,
    prompt_changes: dict[str, str] | None,
    reason: str,
    date: str,
) -> None:
    path = Path(prompts_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_default_prompts_md(), encoding="utf-8")
    text = path.read_text(encoding="utf-8")

    if param_changes:
        for key, value in param_changes.items():
            if key.startswith("source_weights."):
                source = key.split(".", 1)[1]
                if re.search(rf"- {source}:", text):
                    text = re.sub(
                        rf"(## source_weights.*?- {source}:\s*)[0-9.]+",
                        rf"\g<1>{value}",
                        text,
                        flags=re.DOTALL,
                    )
                else:
                    # 新規エントリを source_weights セクションの末尾に追加
                    text = re.sub(
                        r"(## source_weights\n(?:  - [^\n]+\n)*)",
                        rf"\g<1>  - {source}: {value}\n",
                        text,
                    )
            elif key.startswith("topic_quotas."):
                text = _set_topic_quota(text, key.split(".", 1)[1], int(value))
            else:
                text = re.sub(
                    rf"({key}:\s*)[0-9.]+",
                    rf"\g<1>{value}",
                    text,
                )

    if prompt_changes:
        for prompt_key, new_text in prompt_changes.items():
            if re.search(rf"^## {re.escape(prompt_key)}\n", text, re.MULTILINE):
                text = re.sub(
                    rf"(## {re.escape(prompt_key)}\n).*?(?=\n## |\Z)",
                    lambda m: f"{m.group(1)}{new_text}\n",
                    text,
                    flags=re.DOTALL,
                )
            else:
                # 追加された判定基準など、まだ存在しないセクションは新規に追加する
                text = _insert_section(text, f"## {prompt_key}\n\n{new_text}\n")

    history_entry = f"| {date} | {reason} |"
    if "## 改善履歴" in text:
        section_m = re.search(r"## 改善履歴\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if section_m:
            lines = section_m.group(1).splitlines()
            data_rows = [
                l for l in lines
                if l.strip().startswith("|")
                and not re.match(r"^\s*\|[-\s|]+\|\s*$", l)
                and not re.match(r"^\s*\|\s*date\s*\|", l, re.IGNORECASE)
            ]
            rows_text = "\n".join([history_entry] + data_rows)
            new_section = f"## 改善履歴\n| date | reason |\n|------|--------|\n{rows_text}\n"
            text = text[: section_m.start()] + new_section + text[section_m.end():]
    else:
        text += f"\n## 改善履歴\n| date | reason |\n|------|--------|\n{history_entry}\n"

    path.write_text(text, encoding="utf-8")
