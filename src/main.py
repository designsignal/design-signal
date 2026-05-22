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

import sys
from datetime import datetime, timedelta, timezone

from . import state
from .compose import compose_post
from .config import Config
from .fetch import fetch_all
from .publish import notify_user, send_to_channel
from .score import score_batch

# Don't score articles older than this — daily digest is about FRESH news.
# Anything older than 3 days is stale and not worth spending tokens on.
MAX_ARTICLE_AGE_DAYS = 3
# Top-N freshest items per run. With 3 runs/day × 15 = ~45 articles/day max.
MAX_TO_SCORE_PER_RUN = 15
# Max items per single source per run. Stops arXiv (20+ papers/day) from
# flooding the freshest-15 slots and starving real AI-design news sources.
MAX_PER_SOURCE = 2


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
