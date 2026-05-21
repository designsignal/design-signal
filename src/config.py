"""
Loads environment variables. Supports both GitHub Actions (env directly)
and local .env file (via python-dotenv if installed, else falls back to OS env).
"""

import os
import sys
from pathlib import Path

# Try to load .env file for local testing (optional)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed; env vars must come from OS


def _get(name: str, required: bool = True, default: str = "") -> str:
    val = os.environ.get(name, default).strip()
    if required and not val:
        print(f"ERROR: missing required env var {name}", file=sys.stderr)
        sys.exit(1)
    return val


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on")


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID = _get("TELEGRAM_CHANNEL_ID")
    TELEGRAM_USER_ID = _get("TELEGRAM_USER_ID", required=False)  # for safety-gate v2

    # Gemini
    GEMINI_API_KEY = _get("GEMINI_API_KEY")
    GEMINI_MODEL = _get("GEMINI_MODEL", required=False, default="gemini-2.0-flash")

    # Behaviour knobs
    MIN_SCORE_TO_PUBLISH = _get_int("MIN_SCORE_TO_PUBLISH", 8)
    MAX_POSTS_PER_RUN = _get_int("MAX_POSTS_PER_RUN", 2)
    DRY_RUN = _get_bool("DRY_RUN", False)

    # Paths
    ROOT = Path(__file__).parent.parent
    SOURCES_FILE = ROOT / "sources.yaml"
    STATE_FILE = ROOT / "state.json"
    PROMPTS_DIR = ROOT / "prompts"
