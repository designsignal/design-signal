"""
Design Signal — main orchestrator.

Pipeline:
  1. Fetch all RSS sources (Layer 1)
  2. Dedupe vs state.json
  3. Filter recent (last 14 days) to avoid posting old articles
  4. Score each new article with Gemini
  5. Pick top N (above threshold)
  6. Compose Ukrainian post for each
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

# Don't score articles older than this — avoid scoring noise
MAX_ARTICLE_AGE_DAYS = 14
# Don't score more than this per run — paid tier handles 80 easily, ~$0.04 per run
MAX_TO_SCORE_PER_RUN = 80


def main() -> int:
    print(f"=== Design Signal run @ {datetime.now(timezone.utc).isoformat()} ===")
    print(f"Scoring model:   {Config.GEMINI_SCORING_MODEL}")
    print(f"Composing model: {Config.GEMINI_COMPOSING_MODEL}")
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

    # 4. Cap items to score per run
    to_score = unseen[:MAX_TO_SCORE_PER_RUN]
    if len(unseen) > MAX_TO_SCORE_PER_RUN:
        print(f"Capping to top {MAX_TO_SCORE_PER_RUN} most-recent items for scoring")

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
