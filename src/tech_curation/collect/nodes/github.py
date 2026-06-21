"""GitHub node: fetches trending repositories and recent releases via PyGitHub."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from github import Github, GithubException, RateLimitExceededException

from tech_curation.collect.state import CollectedItem, CollectState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _search_repos(gh: Github, query: str, max_items: int) -> list[CollectedItem]:
    items: list[CollectedItem] = []
    try:
        repos = gh.search_repositories(query=query, sort="stars", order="desc")
        for repo in repos[:max_items]:
            path = repo.full_name  # "owner/repo"
            items.append(
                CollectedItem(
                    id=str(uuid.uuid4()),
                    title=repo.full_name,
                    url=repo.html_url,
                    source="github",
                    published=repo.pushed_at.isoformat() if repo.pushed_at else _now_iso(),
                    body=repo.description or "",
                    relevance_score=0.0,
                    summary="",
                    content_type="",
                    thumbnail=f"https://opengraph.githubassets.com/1/{path}",
                    topic="",
                )
            )
    except RateLimitExceededException:
        raise  # 呼び出し元でキャッチして全クエリをスキップ
    except GithubException:
        pass
    return items


def github_node(state: CollectState) -> CollectState:
    token = os.environ.get("GITHUB_TOKEN")
    # retry=False でレートリミット時の自動バックオフを無効化
    gh = Github(token, retry=False) if token else Github(retry=False)

    config = state["config"]
    weight = config.source_weights.get("github", 0.8)
    total_budget = config.max_items_per_run
    max_items = max(1, round(total_budget * weight))

    items: list[CollectedItem] = []
    errors: list[str] = []

    for topic, queries in state.get("queries", {}).items():
        for query in queries:
            try:
                fetched = _search_repos(gh, query, max_items // max(len(queries), 1))
                items.extend(fetched)
            except RateLimitExceededException:
                errors.append("github:rate_limit_exceeded (set GITHUB_TOKEN to increase quota)")
                return {"raw_items": items, "errors": errors}
            except Exception as exc:
                errors.append(f"github:{query}:{exc}")

    return {"raw_items": items, "errors": errors}
