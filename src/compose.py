"""
Composes a Telegram post in Ukrainian about a high-scoring article.
"""

import google.generativeai as genai

from .config import Config


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "compose.txt").read_text()


_MODEL = None
_PROMPT = None


def _get_model():
    global _MODEL, _PROMPT
    if _MODEL is None:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _MODEL = genai.GenerativeModel(
            Config.GEMINI_COMPOSING_MODEL,
            generation_config={
                "temperature": 0.7,        # more creative for writing
                "max_output_tokens": 1200,
            },
        )
        _PROMPT = _load_prompt()
        print(f"Composing model: {Config.GEMINI_COMPOSING_MODEL}")
    return _MODEL


def compose_post(item: dict) -> str | None:
    """Generate Telegram-ready post text. Returns None on failure."""
    model = _get_model()
    prompt = _PROMPT.format(
        title=item.get("title", "")[:300],
        source_name=item.get("source_name", "unknown"),
        url=item.get("url", ""),
        summary=item.get("summary", "")[:2000],
        score_reason=item.get("score_reason", ""),
    )

    try:
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        # Strip code fences if Gemini wrapped output
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(line for line in lines if not line.strip().startswith("```"))
        # Safety: enforce max length for Telegram
        if len(text) > 1200:
            text = text[:1180] + "..."
        return text.strip() if text else None
    except Exception as e:
        print(f"  [compose-err] {type(e).__name__}: {e}")
        return None
