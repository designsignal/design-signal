"""
Scores articles 0-10 using Claude Haiku. Strict JSON output expected.

Outage handling:
  - 3 retries per item with adaptive backoff (20s/45s/90s + jitter)
  - If 4+ items hit 529 overload in a row, abandon the pass to save workflow time
  - If the pass bailed OR 33%+ items failed → sleep OUTAGE_RETRY_DELAY (10 min)
    and retry just the failed items once more.
  - Notify user via Telegram DM when outage detected.
"""

import json
import random
import re
import time

import anthropic

from .config import Config

# Result sentinels for items that failed transient API issues (vs genuinely scored 0).
_OVERLOAD_MARKER = "__OVERLOADED__"
_SKIPPED_MARKER = "__SKIPPED_OUTAGE__"

# How long to wait before retrying when Anthropic outage is detected (seconds).
OUTAGE_RETRY_DELAY = 600   # 10 minutes
# How many consecutive overloads trigger the "bail out of current pass" logic.
BAIL_THRESHOLD = 4


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "scoring.txt").read_text()


_CLIENT = None
_PROMPT = None


def _get_client():
    global _CLIENT, _PROMPT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        _PROMPT = _load_prompt()
    return _CLIENT


def _parse_json(text: str) -> dict | None:
    """Tolerant JSON extraction — model sometimes wraps in markdown."""
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def score_item(item: dict, retries: int = 2) -> dict:
    """Returns item with added 'score', 'score_reason', 'topic_tags'.

    On 529 overload, marks score_reason=_OVERLOAD_MARKER so the batch can
    distinguish transient failure from a genuine low score.
    """
    client = _get_client()
    prompt = _PROMPT.format(
        title=item.get("title", "")[:300],
        source_name=item.get("source_name", "unknown"),
        source_tags=", ".join(item.get("source_tags", [])),
        url=item.get("url", ""),
        summary=item.get("summary", "")[:800],
    )

    # Adaptive backoff: 20s, 45s, 90s with ±20% jitter to avoid thundering herd.
    overload_waits = [20, 45, 90]
    overloaded_failure = False

    for attempt in range(retries + 1):
        try:
            resp = client.messages.create(
                model=Config.CLAUDE_SCORING_MODEL,
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in resp.content if hasattr(block, "text"))
            data = _parse_json(text)
            if data and "score" in data:
                raw_score = float(data.get("score", 0))
                weight = float(item.get("source_weight", 1.0))
                final_score = round(raw_score * (0.7 + 0.3 * weight), 2)
                return {
                    **item,
                    "score": min(10.0, final_score),
                    "score_raw": raw_score,
                    "score_reason": data.get("reason", ""),
                    "topic_tags": data.get("topic_tags", []),
                }
        except anthropic.RateLimitError as e:
            wait = 30
            try:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    wait = int(retry_after) + 2
            except (AttributeError, ValueError, TypeError):
                pass
            print(f"  [rate-limit] sleeping {wait}s before retry...")
            time.sleep(wait)
            continue
        except anthropic.InternalServerError:
            overloaded_failure = True
            if attempt < retries:
                base = overload_waits[min(attempt, len(overload_waits) - 1)]
                wait = int(base * random.uniform(0.8, 1.2))
                print(f"  [overloaded] sleeping {wait}s before retry "
                      f"(attempt {attempt + 1}/{retries + 1})...")
                time.sleep(wait)
                continue
            else:
                print(f"  [overloaded] giving up on '{item.get('title', '')[:50]}'")
                break
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            short_err = str(e).split("\n")[0][:120]
            print(f"  [score-err] {item.get('title', '')[:40]}: {type(e).__name__}: {short_err}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            short_err = str(e).split("\n")[0][:120]
            print(f"  [score-err] {item.get('title', '')[:40]}: {type(e).__name__}: {short_err}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
        break

    # Mark overload distinctly so the batch can detect a sustained outage.
    reason = _OVERLOAD_MARKER if overloaded_failure else "scoring failed"
    return {**item, "score": 0.0, "score_raw": 0.0, "score_reason": reason, "topic_tags": []}


def _is_transient_failure(item: dict) -> bool:
    """True if item failed due to API outage (vs genuinely scored 0)."""
    return item.get("score_reason") in (_OVERLOAD_MARKER, _SKIPPED_MARKER)


def _score_pass(items: list[dict], rpm_limit: int, pass_label: str = "") -> list[dict]:
    """Single pass through items. Bails early after BAIL_THRESHOLD consecutive overloads."""
    delay = 60.0 / rpm_limit
    scored: list[dict] = []
    consecutive_overloads = 0

    for i, item in enumerate(items, 1):
        result = score_item(item)
        scored.append(result)

        if result.get("score_reason") == _OVERLOAD_MARKER:
            consecutive_overloads += 1
        else:
            consecutive_overloads = 0

        if consecutive_overloads >= BAIL_THRESHOLD:
            print(f"  [bail{pass_label}] {BAIL_THRESHOLD} consecutive overloads — "
                  f"Anthropic appears down. Stopping at {i}/{len(items)}.")
            for skipped in items[i:]:
                scored.append({**skipped, "score": 0.0, "score_raw": 0.0,
                               "score_reason": _SKIPPED_MARKER, "topic_tags": []})
            return scored

        if i % 5 == 0 or i == len(items):
            top = sorted(scored, key=lambda x: x["score"], reverse=True)[:3]
            top_str = "  ".join(f"{t['score']:.1f}={t['title'][:40]}" for t in top)
            print(f"  scored{pass_label} {i}/{len(items)} — top so far: {top_str}")
        if i < len(items):
            time.sleep(delay)

    return scored


def _notify_outage(message: str) -> None:
    """Best-effort DM to bot owner. Import here to avoid circular imports at module load."""
    try:
        from .publish import notify_user
        notify_user(message)
    except Exception as e:
        print(f"  [notify-err] {type(e).__name__}: {e}")


def score_batch(items: list[dict], rpm_limit: int = 30) -> list[dict]:
    """Score items, with outage-aware retry pass.

    Strategy:
      1. First pass — score everything, bail early on sustained overload.
      2. If 33%+ items failed transiently → sleep OUTAGE_RETRY_DELAY, do second pass
         on only the failed items.
      3. If second pass also fails widely → notify user and return what we have.
    """
    print(f"Scoring {len(items)} items with {Config.CLAUDE_SCORING_MODEL}...")
    scored = _score_pass(items, rpm_limit)

    transient_failed_idx = [i for i, s in enumerate(scored) if _is_transient_failure(s)]
    failure_ratio = len(transient_failed_idx) / max(len(scored), 1)

    if not transient_failed_idx:
        return scored

    if failure_ratio < 0.33 and len(transient_failed_idx) < BAIL_THRESHOLD:
        # Few enough failures that it's not worth waiting 10 min
        print(f"  [info] {len(transient_failed_idx)} transient failures — not retrying "
              f"(below outage threshold)")
        return scored

    # Outage detected — sleep and retry only the failed items.
    minutes = OUTAGE_RETRY_DELAY // 60
    print(f"\n[outage-recovery] {len(transient_failed_idx)} of {len(scored)} items "
          f"failed due to Anthropic overload. Sleeping {minutes} min then retrying...")
    _notify_outage(
        f"[Design Signal] Anthropic API overload during run — "
        f"{len(transient_failed_idx)}/{len(scored)} items hit 529. "
        f"Sleeping {minutes} min then retrying just those items."
    )
    time.sleep(OUTAGE_RETRY_DELAY)

    to_retry = [scored[i] for i in transient_failed_idx]
    print(f"\n[outage-recovery] Retrying {len(to_retry)} previously-failed items...")
    retried = _score_pass(to_retry, rpm_limit, pass_label=" (retry)")

    # Splice retried results back into scored.
    for original_idx, new_result in zip(transient_failed_idx, retried):
        scored[original_idx] = new_result

    # Final check — did the retry rescue most items?
    still_failed = sum(1 for s in retried if _is_transient_failure(s))
    if still_failed >= BAIL_THRESHOLD or (still_failed / max(len(retried), 1)) >= 0.5:
        _notify_outage(
            f"[Design Signal] Anthropic still overloaded after 10-min retry. "
            f"{still_failed}/{len(retried)} items still failing. "
            f"Skipping this run; next hourly cron will try again."
        )
        print(f"[outage-recovery] {still_failed} items still failing after retry. "
              f"Anthropic likely in extended outage.")
    else:
        print(f"[outage-recovery] Retry rescued {len(retried) - still_failed}/{len(retried)} items.")

    return scored
