"""
Scores articles 0-10 using Gemini. Strict JSON output expected.
"""

import json
import re
import time
from pathlib import Path

import google.generativeai as genai

from .config import Config


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "scoring.txt").read_text()


def _init_model():
    genai.configure(api_key=Config.GEMINI_API_KEY)
    return genai.GenerativeModel(
        Config.GEMINI_MODEL,
        generation_config={
            "temperature": 0.3,           # consistency over creativity for scoring
            "response_mime_type": "application/json",
            "max_output_tokens": 300,
        },
    )


_MODEL = None
_PROMPT = None


def _get_model():
    global _MODEL, _PROMPT
    if _MODEL is None:
        _MODEL = _init_model()
        _PROMPT = _load_prompt()
    return _MODEL


def _parse_json(text: str) -> dict | None:
    """Tolerant JSON extraction — Gemini sometimes wraps in markdown."""
    if not text:
        return None
    # Strip markdown fences if present
    text = text.strip()
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
    model = _get_model()
    prompt = _PROMPT.format(
        title=item.get("title", "")[:300],
        source_name=item.get("source_name", "unknown"),
        source_tags=", ".join(item.get("source_tags", [])),
        url=item.get("url", ""),
        summary=item.get("summary", "")[:1500],
    )

    for attempt in range(retries + 1):
        try:
            resp = model.generate_content(prompt)
            data = _parse_json(resp.text)
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
        except Exception as e:
            print(f"  [score-err] {item.get('title', '')[:50]}: {type(e).__name__}: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)  # backoff
                continue
        break

    # Fallback: zero score on failure
    return {**item, "score": 0.0, "score_raw": 0.0, "score_reason": "scoring failed", "topic_tags": []}


def score_batch(items: list[dict], rpm_limit: int = 12) -> list[dict]:
    """Score items one by one with rate limiting (Gemini free tier = 15 RPM)."""
    print(f"Scoring {len(items)} items with {Config.GEMINI_MODEL}...")
    delay = 60.0 / rpm_limit
    scored = []
    for i, item in enumerate(items, 1):
        result = score_item(item)
        scored.append(result)
        if i % 10 == 0 or i == len(items):
            top = sorted(scored, key=lambda x: x["score"], reverse=True)[:3]
            top_str = "  ".join(f"{t['score']:.1f}={t['title'][:40]}" for t in top)
            print(f"  scored {i}/{len(items)} — top so far: {top_str}")
        if i < len(items):
            time.sleep(delay)
    return scored
