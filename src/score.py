"""
Scores articles 0-10 using Claude Haiku. Strict JSON output expected.
"""

import json
import re
import time

import anthropic

from .config import Config


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
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object inside
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def score_item(item: dict, retries: int = 2) -> dict:
    """Returns item with added 'score', 'score_reason', 'topic_tags' keys."""
    client = _get_client()
    # Tight summary cap — saves ~50% input tokens vs old 1500-char cap.
    # Haiku doesn't need long context for scoring decisions.
    prompt = _PROMPT.format(
        title=item.get("title", "")[:300],
        source_name=item.get("source_name", "unknown"),
        source_tags=", ".join(item.get("source_tags", [])),
        url=item.get("url", ""),
        summary=item.get("summary", "")[:800],
    )

    for attempt in range(retries + 1):
        try:
            resp = client.messages.create(
                model=Config.CLAUDE_SCORING_MODEL,
                max_tokens=300,
                temperature=0.3,  # consistency over creativity for scoring
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in resp.content if hasattr(block, "text"))
            data = _parse_json(text)
            if data and "score" in data:
                raw_score = float(data.get("score", 0))
                # Apply source weight as multiplier (small boost for trusted sources)
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
            # Honor Anthropic's retry-after header if present
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
        except anthropic.InternalServerError as e:
            # 529 overloaded_error — Anthropic transient overload, longer backoff
            wait = 15 * (2 ** attempt)  # 15s, 30s, 60s
            print(f"  [overloaded] sleeping {wait}s before retry (attempt {attempt + 1}/{retries + 1})...")
            time.sleep(wait)
            continue
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            short_err = str(e).split("\n")[0][:120]
            print(f"  [score-err] {item.get('title', '')[:40]}: {type(e).__name__}: {short_err}")
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff
                continue
        except Exception as e:
            short_err = str(e).split("\n")[0][:120]
            print(f"  [score-err] {item.get('title', '')[:40]}: {type(e).__name__}: {short_err}")
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
        break

    # Fallback: zero score on failure
    return {**item, "score": 0.0, "score_raw": 0.0, "score_reason": "scoring failed", "topic_tags": []}


def score_batch(items: list[dict], rpm_limit: int = 30) -> list[dict]:
    """Score items with rate limiting. Claude Tier 1 = 50 RPM for Haiku, 30 is safe."""
    print(f"Scoring {len(items)} items with {Config.CLAUDE_SCORING_MODEL}...")
    delay = 60.0 / rpm_limit
    scored = []
    for i, item in enumerate(items, 1):
        result = score_item(item)
        scored.append(result)
        if i % 5 == 0 or i == len(items):
            top = sorted(scored, key=lambda x: x["score"], reverse=True)[:3]
            top_str = "  ".join(f"{t['score']:.1f}={t['title'][:40]}" for t in top)
            print(f"  scored {i}/{len(items)} — top so far: {top_str}")
        if i < len(items):
            time.sleep(delay)
    return scored
