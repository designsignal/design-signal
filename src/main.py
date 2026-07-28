"""
Design Signal — main orchestrator.

Pipeline:
  1. Fetch all RSS sources (Layer 1)
  2. Dedupe vs state.json
  3. Filter recent (last 3 days) — daily digest needs fresh content
  4. Score each new article with Claude Haiku
  5. Pick top N (above threshold)
  6. Compose Ukrainian post for each with Claude Sonnet
  7. Publish to Telegram
  8. Save state

Run locally:    python -m src.main
Dry-run:        DRY_RUN=true python -m src.main
"""

import difflib
import sys
from datetime import datetime, timedelta, timezone

from . import state
from .compose import compose_post
from .config import Config
from .fetch import fetch_all
from .publish import notify_user, send_to_channel
from .score import score_batch


def _titles_similar(a: str, b: str, threshold: float = 0.72) -> bool:
    """True if two normalized titles describe the same story."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = set(a.split()), set(b.split())
    if ta and tb and len(ta & tb) / min(len(ta), len(tb)) >= 0.8:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold


def _dedupe(items: list, recent: list) -> list:
    """Drop items whose title matches another kept item or a recently published one."""
    kept, norms = [], []
    for it in items:
        nt = state.norm_title(it.get("title", ""))
        if any(_titles_similar(nt, r) for r in recent):
            continue
        if any(_titles_similar(nt, k) for k in norms):
            continue
        kept.append(it)
        norms.append(nt)
    return kept


def _is_blocked_source(item: dict) -> bool:
    """Drop low-trust outlets (crypto, PR wires, stock sites) before scoring."""
    hay = ((item.get("source_publisher") or "") + " " + (item.get("url") or "")).lower()
    return any(b in hay for b in BLOCKED_SOURCES)


def _resolve_url(url: str) -> str:
    """Decode a Google News RSS redirect to the real source URL. Best-effort."""
    if not url or "news.google.com" not in url:
        return url
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(url, interval=1)
        dec = r.get("decoded_url") if isinstance(r, dict) else None
        if dec and str(dec).startswith("http"):
            return dec
    except Exception as e:
        print(f"  [decode-skip] {type(e).__name__}")
    return url

# Don't score articles older than this — daily digest is about FRESH news.
# Anything older than 3 days is stale and not worth spending tokens on.
MAX_ARTICLE_AGE_DAYS = 3
# Top-N freshest items per run. Bumped 15->20 so scoring has more on-brand
# candidates to choose from now that sources are design-first (v4).
MAX_TO_SCORE_PER_RUN = 20
# Max items per single source per run. Keeps any one feed (e.g. a busy Google
# News query) from monopolizing the freshest-N slots and starving other sources.
MAX_PER_SOURCE = 2
# Pacing: never publish more than this many posts across all runs in one UTC day.
# Combined with a small MAX_POSTS_PER_RUN and frequent cron triggers, this spaces
# posts out instead of dumping a wall at once.
DAILY_CAP = 4
# Low-trust outlets dropped before scoring — crypto exchanges, PR wires, stock
# tickers. They surface via Google News but never belong in a design digest.
BLOCKED_SOURCES = (
    "kucoin", "coindesk", "cointelegraph", "binance", "crypto.news",
    "benzinga", "tradingview", "marketbeat", "zacks", "motley fool",
    "tipranks", "simply wall", "stocktwits", "investing.com",
    "globenewswire", "prnewswire", "pr newswire", "businesswire",
    "business wire", "accesswire", "einpresswire", "einnews", "24-7pressrelease",
)


def main() -> int:
    print(f"=== Design Signal run @ {datetime.now(timezone.utc).isoformat()} ===")
    print(f"Scoring model:   {Config.CLAUDE_SCORING_MODEL}")
    print(f"Composing model: {Config.CLAUDE_COMPOSING_MODEL}")
    print(f"Min score to publish: {Config.MIN_SCORE_TO_PUBLISH}")
    print(f"Max posts per run: {Config.MAX_POSTS_PER_RUN}")
    print(f"Dry run: {Config.DRY_RUN}")
    print()

    # 1. Fetch
    items = fetch_all(Config.SOURCES_FILE)
    if not items:
        print("No items fetched. Done.")
        return 0

    # 2. Filter by age
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    recent = [i for i in items if (i.get("published_at") or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    print(f"Recent (<{MAX_ARTICLE_AGE_DAYS}d): {len(recent)}")

    # Drop low-trust outlets (crypto/PR/stock) before anything else.
    before_block = len(recent)
    recent = [i for i in recent if not _is_blocked_source(i)]
    if before_block != len(recent):
        print(f"Blocked low-trust sources: -{before_block - len(recent)}")

    # 3. Dedupe vs already-published
    st = state.load(Config.STATE_FILE)
    unseen = state.filter_unseen(st, recent)
    print(f"Unseen: {len(unseen)} (already published: {len(recent) - len(unseen)})")

    if not unseen:
        print("Nothing new to consider. Done.")
        return 0

    # 4. Sort by recency (newest first), then apply per-source cap, then take top-N.
    # Per-source cap prevents any single feed (e.g. arXiv with 20+ papers/day)
    # from monopolizing the freshest-N slots.
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    unseen_sorted = sorted(unseen, key=lambda x: x.get("published_at") or epoch, reverse=True)
    per_source_count: dict[str, int] = {}
    diversified: list[dict] = []
    for itm in unseen_sorted:
        src = itm.get("source_name", "unknown")
        if per_source_count.get(src, 0) >= MAX_PER_SOURCE:
            continue
        per_source_count[src] = per_source_count.get(src, 0) + 1
        diversified.append(itm)

    # Fuzzy-dedupe by title: kills same-story repeats across Google News queries
    # and stories we already published in recent runs (URL dedup misses these).
    before_dedup = len(diversified)
    diversified = _dedupe(diversified, state.recent_titles(st, 60))
    print(f"After title-dedupe: {len(diversified)} (removed {before_dedup - len(diversified)} near-dups)")

    to_score = diversified[:MAX_TO_SCORE_PER_RUN]
    print(f"After per-source cap ({MAX_PER_SOURCE}/source): {len(diversified)} candidates, "
          f"scoring top {len(to_score)}")

    # 5. Score
    scored = score_batch(to_score)

    # 6. Pick winners
    winners = sorted(
        [s for s in scored if s.get("score", 0) >= Config.MIN_SCORE_TO_PUBLISH],
        key=lambda x: x["score"],
        reverse=True,
    )[:Config.MAX_POSTS_PER_RUN]

    print(f"\nWinners (score >= {Config.MIN_SCORE_TO_PUBLISH}): {len(winners)}")
    for w in winners:
        print(f"  {w['score']:.1f} | {w['title'][:80]} | {w['source_name']}")

    # Resolve Google News redirects to real source URLs (clean links) and use the
    # resolved URL as a final dedupe guard against already-published stories.
    seen_keys = set()
    resolved = []
    for w in winners:
        w["url"] = _resolve_url(w.get("url", ""))
        key = state._url_key(w["url"])
        if key in seen_keys or state.is_published(st, w["url"]):
            print(f"  [dup-skip] {w['title'][:60]}")
            continue
        seen_keys.add(key)
        resolved.append(w)
    winners = resolved

    # Daily pacing cap — never exceed DAILY_CAP posts per UTC day across all runs.
    already_today = state.published_today_count(st)
    remaining_today = max(0, DAILY_CAP - already_today)
    if len(winners) > remaining_today:
        print(f"  [daily-cap] {already_today} already posted today; "
              f"trimming winners {len(winners)} -> {remaining_today}")
        winners = winners[:remaining_today]

    if not winners:
        print("\nNo articles above threshold this run. Done.")
        if not Config.DRY_RUN:
            notify_user(f"[Design Signal] Run finished — 0 publishable items. Top: " +
                        ", ".join(f"{s['score']:.1f}" for s in sorted(scored, key=lambda x: x['score'], reverse=True)[:3]))
        return 0

    # 7. Compose + publish
    published_count = 0
    for win in winners:
        print(f"\nComposing post for: {win['title'][:60]}")
        post = compose_post(win)
        if not post:
            print("  [skip] compose returned empty")
            continue

        ok = send_to_channel(post, dry_run=Config.DRY_RUN)
        if ok and not Config.DRY_RUN:
            state.record_published(st, win["url"], win["title"], win["score"])
            published_count += 1
        elif Config.DRY_RUN:
            published_count += 1  # count for reporting even in dry-run

    # 8. Save state
    if not Config.DRY_RUN and published_count > 0:
        state.save(st, Config.STATE_FILE)
        print(f"\nState saved. Published {published_count} post(s).")
        notify_user(f"[Design Signal] Published {published_count} post(s) this run.")
    elif Config.DRY_RUN:
        print(f"\nDry run finished. Would publish {published_count} post(s).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
