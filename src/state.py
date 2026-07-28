"""
Simple JSON-file state — tracks URLs we've already published, so we don't repost.
Committed back to repo by GitHub Actions after each run.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Iterable

MAX_ENTRIES = 5000  # rotate old after this; protects state.json from infinite growth

_STOP = {"the", "a", "an", "to", "for", "of", "in", "on", "and", "or", "is",
         "now", "with", "your", "you", "how", "why", "new", "de", "la"}


def norm_title(title: str) -> str:
    """Lowercase, strip punctuation, drop stopwords — for fuzzy dup comparison."""
    t = re.sub(r"[^\w\s]", " ", (title or "").lower())
    toks = [w for w in t.split() if w not in _STOP and len(w) > 2]
    return " ".join(toks)


def recent_titles(state: dict, n: int = 60) -> list:
    """Normalized titles of the last n published items — for cross-run dedup."""
    pub = state.get("published", [])[-n:]
    return [norm_title(e.get("title", "")) for e in pub if e.get("title")]


def published_today_count(state: dict) -> int:
    """How many posts were published today (UTC) — for the daily pacing cap."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    return sum(1 for e in state.get("published", [])
               if str(e.get("published_at", "")).startswith(today))


def _url_key(url: str) -> str:
    """Normalize URL for stable comparison: strip tracking params, lowercase, hash."""
    base = url.split("?")[0].split("#")[0].strip().rstrip("/").lower()
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def load(path: Path) -> dict:
    """Load state from disk, or create empty if missing."""
    if not path.exists():
        return {"published": []}
    try:
        with open(path) as f:
            data = json.load(f)
        if "published" not in data:
            data["published"] = []
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: state file corrupt ({e}), starting fresh")
        return {"published": []}


def save(state: dict, path: Path) -> None:
    """Persist state to disk atomically."""
    # Rotate if too many entries
    if len(state.get("published", [])) > MAX_ENTRIES:
        state["published"] = state["published"][-MAX_ENTRIES:]
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def is_published(state: dict, url: str) -> bool:
    """Check if URL has already been published."""
    key = _url_key(url)
    return any(entry.get("key") == key for entry in state.get("published", []))


def filter_unseen(state: dict, items: Iterable[dict]) -> list[dict]:
    """Return only items whose URL we haven't published before."""
    seen_keys = {entry["key"] for entry in state.get("published", []) if "key" in entry}
    out = []
    for it in items:
        url = it.get("url") or it.get("link")
        if not url:
            continue
        if _url_key(url) in seen_keys:
            continue
        out.append(it)
    return out


def record_published(state: dict, url: str, title: str, score: float) -> None:
    """Add URL to published history."""
    state.setdefault("published", []).append({
        "key": _url_key(url),
        "url": url,
        "title": title[:200],
        "score": round(score, 2),
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
