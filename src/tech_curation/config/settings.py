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
}


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

    return cfg


def _default_prompts_md() -> str:
    cfg = AgentConfig()
    weights = "\n".join(f"  - {k}: {v}" for k, v in cfg.source_weights.items())
    return (
        f"## source_weights\n{weights}\n\n"
        f"filter_threshold: {cfg.filter_threshold}\n"
        f"recency_days: {cfg.recency_days}\n"
        f"max_items_per_run: {cfg.max_items_per_run}\n\n"
        f"## query_gen_prompt\n{cfg.query_gen_prompt}\n\n"
        f"## relevance_score_prompt\n{cfg.relevance_score_prompt}\n\n"
        f"## summarize_prompt\n{cfg.summarize_prompt}\n\n"
        f"## content_type_prompt\n{cfg.content_type_prompt}\n"
    )


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
                text = re.sub(
                    rf"(## source_weights.*?- {source}:\s*)[0-9.]+",
                    rf"\g<1>{value}",
                    text,
                    flags=re.DOTALL,
                )
            else:
                text = re.sub(
                    rf"({key}:\s*)[0-9.]+",
                    rf"\g<1>{value}",
                    text,
                )

    if prompt_changes:
        for prompt_key, new_text in prompt_changes.items():
            text = re.sub(
                rf"(## {prompt_key}\n).*?(?=\n## |\Z)",
                rf"\g<1>{new_text}\n",
                text,
                flags=re.DOTALL,
            )

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
