"""Plan node: reads topics.md and generates search queries via LLM."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tech_curation.collect.state import CollectState
from tech_curation.llm import chat

TOPICS_VAULT_PATH = "agent-config/topics.md"
POLICY_VAULT_PATH = "agent-config/policy.md"


def _parse_active_topics(topics_md: str) -> list[str]:
    lines = topics_md.splitlines()
    in_active = False
    topics: list[str] = []
    for line in lines:
        if line.strip() == "## アクティブ":
            in_active = True
            continue
        if line.startswith("## ") and line.strip() != "## アクティブ":
            in_active = False
        if in_active and line.strip().startswith("- "):
            topics.append(line.strip().lstrip("- ").strip())
    return topics


def _generate_queries(topic: str, prompt: str, policy: str = "") -> list[str]:
    policy_section = f"\n\nUser's standing policy:\n{policy}" if policy else ""
    text = chat(
        [{"role": "user", "content": f"{prompt}{policy_section}\n\nTopic: {topic}"}],
        max_tokens=256,
    )
    try:
        queries = json.loads(text)
        if isinstance(queries, list):
            return [str(q) for q in queries]
    except json.JSONDecodeError:
        pass
    return [f"{topic} 2026", f"{topic} release", f"{topic} tutorial"]


def plan_node(state: CollectState) -> CollectState:
    # ob sync は handler 側で実行済み。ここでは vault_root を読むだけ。
    vault_root = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
    topics_path = vault_root / TOPICS_VAULT_PATH
    if topics_path.exists():
        topics_md = topics_path.read_text(encoding="utf-8")
        topics = _parse_active_topics(topics_md)
    else:
        topics = state.get("topics", [])

    prompts_path = vault_root / "agent-config" / "prompts.md"
    if prompts_path.exists():
        from tech_curation.config.settings import load_config
        config = load_config(prompts_path)
    else:
        config = state["config"]

    policy_path = vault_root / POLICY_VAULT_PATH
    policy = policy_path.read_text(encoding="utf-8") if policy_path.exists() else ""

    queries: dict[str, list[str]] = {}
    for topic in topics:
        queries[topic] = _generate_queries(topic, config.query_gen_prompt, policy)

    return {
        "topics": topics,
        "config": config,
        "queries": queries,
    }
