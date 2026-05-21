"""
RSS fetching — parallel, with timeouts, normalized output.
Only fetches Layer 1 (primary sources) for v1 MVP.
Layer 2 (signals) and Layer 3 (competitors) come in v2.
"""

import concurrent.futures
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import yaml

USER_AGENT = "Mozilla/5.0 DesignSignalBot/1.0 (+https://t.me/design_signal)"
TIMEOUT = 15
MAX_ITEMS_PER_FEED = 20  # don't pull entire archive
MAX_WORKERS = 12


def _flatten_layer1(cfg: dict) -> list[dict]:
    """Extract all sources from layer_1_primary."""
    out = []
    layer1 = cfg.get("layer_1_primary", {})
    for category, items in layer1.items():
        if not isinstance(items, list):
            continue
        for src in items:
            if isinstance(src, dict) and "url" in src:
                # Skip Telegram sources (handled separately) and twitter (often dead)
                url = src["url"]
                if url.startswith("tg://") or "xcancel.com" in url:
                    continue
                out.append({**src, "category": category})
    return out


def _parse_dt(entry) -> Optional[datetime]:
    """Best-effort timestamp parsing from feedparser entry."""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def _clean_text(html: str, max_len: int = 2000) -> str:
    """Strip HTML tags and trim."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _fetch_one(source: dict) -> list[dict]:
    """Fetch single RSS source; never raises."""
    url = source["url"]
    name = source["name"]
    weight = float(source.get("weight", 1.0))
    try:
        # feedparser handles timeouts via socket; set ssl/timeout via request_headers
        parsed = feedparser.parse(
            url,
            request_headers={"User-Agent": USER_AGENT},
        )
        if parsed.bozo and not parsed.entries:
            print(f"  [skip] {name}: parse failed ({parsed.bozo_exception})")
            return []
        items = []
        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            link = entry.get("link") or entry.get("id")
            if not link:
                continue
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = _clean_text(entry.get("summary", "") or entry.get("description", ""))
            content = entry.get("content")
            if content and isinstance(content, list) and content:
                full = _clean_text(content[0].get("value", ""), max_len=4000)
                if len(full) > len(summary):
                    summary = full
            items.append({
                "url": link,
                "title": title,
                "summary": summary,
                "published_at": _parse_dt(entry),
                "source_name": name,
                "source_weight": weight,
                "source_tags": source.get("tags", []),
                "source_category": source.get("category", ""),
                "source_lang": source.get("lang", "en"),
            })
        print(f"  [ok]   {name}: {len(items)} items")
        return items
    except Exception as e:
        print(f"  [err]  {name}: {type(e).__name__}: {e}")
        return []


def fetch_all(sources_file) -> list[dict]:
    """Fetch all Layer 1 RSS feeds in parallel."""
    with open(sources_file) as f:
        cfg = yaml.safe_load(f)
    sources = _flatten_layer1(cfg)
    print(f"Fetching {len(sources)} RSS sources...")

    all_items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for items in pool.map(_fetch_one, sources):
            all_items.extend(items)

    # Sort by published date desc when available (None last)
    all_items.sort(
        key=lambda x: x.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    print(f"Total items fetched: {len(all_items)}")
    return all_items
