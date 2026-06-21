"""FetchContent node: fetches full article text from each item's URL."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup

from tech_curation.collect.state import CollectedItem, CollectState

MAX_CONTENT_CHARS = 3000
FETCH_TIMEOUT = 10
MAX_WORKERS = 8

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; tech-curation-bot/1.0)"
    ),
    "Accept-Language": "ja,en;q=0.9",
}

# フェッチをスキップするドメイン（ログイン必須・bot ブロック等）
_SKIP_DOMAINS = {
    "twitter.com", "x.com", "github.com",
    "linkedin.com", "facebook.com",
}


def _should_skip(url: str) -> bool:
    return any(d in url for d in _SKIP_DOMAINS)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # script / style を除去
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # article > main > body の優先順で本文を探す
    for selector in ["article", "main", '[role="main"]', ".post-content",
                     ".entry-content", ".article-body", "body"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            if len(text) > 200:
                return text[:MAX_CONTENT_CHARS]

    return soup.get_text(separator="\n", strip=True)[:MAX_CONTENT_CHARS]


def _extract_og_image(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
    if tag and tag.get("content"):
        return tag["content"]
    return ""


def _fetch_one(item: CollectedItem) -> CollectedItem:
    url = item["url"]
    if not url or _should_skip(url):
        return item
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=FETCH_TIMEOUT,
                         follow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            updates: dict = {}
            text = _extract_text(resp.text)
            if len(text) > len(item.get("body", "")):
                updates["body"] = text
            thumbnail = _extract_og_image(resp.text)
            if thumbnail and not item.get("thumbnail"):
                updates["thumbnail"] = thumbnail
            if updates:
                return {**item, **updates}
    except Exception:
        pass
    return item


def fetch_content_node(state: CollectState) -> CollectState:
    # relevance filter 後の記事だけを対象にする
    items = list(state.get("filtered_items", []))
    if not items:
        return {"filtered_items": []}

    results: list[CollectedItem] = [None] * len(items)  # type: ignore

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(_fetch_one, item): i for i, item in enumerate(items)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = items[idx]

    fetched = sum(1 for r, orig in zip(results, items) if len(r.get("body", "")) > len(orig.get("body", "")))
    print(f"[fetch_content] fetched={fetched}/{len(items)}")
    return {"filtered_items": results}
