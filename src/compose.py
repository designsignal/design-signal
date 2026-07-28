"""
Composes a Telegram post in Ukrainian about a high-scoring article.
Uses Claude Sonnet for higher-quality creative writing.
"""

from __future__ import annotations

import anthropic

from .config import Config


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "compose.txt").read_text()


_CLIENT = None
_PROMPT = None


def _get_client():
    global _CLIENT, _PROMPT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        _PROMPT = _load_prompt()
        print(f"Composing model: {Config.CLAUDE_COMPOSING_MODEL}")
    return _CLIENT


def compose_post(item: dict) -> str | None:
    """Generate Telegram-ready post text. Returns None on failure."""
    client = _get_client()
    prompt = _PROMPT.format(
        title=item.get("title", "")[:300],
        source_name=item.get("source_name", "unknown"),
        url=item.get("url", ""),
        summary=item.get("summary", "")[:2000],
        score_reason=item.get("score_reason", ""),
    )

    try:
        resp = client.messages.create(
            model=Config.CLAUDE_COMPOSING_MODEL,
            max_tokens=1200,
            temperature=0.7,  # more creative for writing
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        text = (text or "").strip()
        # Strip code fences if model wrapped output
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(line for line in lines if not line.strip().startswith("```"))
        # Kill em/en dashes — a tell of AI text. Channel style uses plain hyphens.
        text = text.replace(" — ", " - ").replace(" – ", " - ").replace("—", "-").replace("–", "-")
        # Safety: enforce max length for Telegram
        if len(text) > 1200:
            text = text[:1180] + "..."
        return text.strip() if text else None
    except Exception as e:
        print(f"  [compose-err] {type(e).__name__}: {e}")
        return None
