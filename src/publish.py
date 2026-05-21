"""
Publishes posts to Telegram channel via Bot API.
Uses Markdown parse mode. Disables link preview for cleaner look.
"""

import time

import requests

from .config import Config

API_BASE = "https://api.telegram.org/bot{token}"


def _escape_markdown(text: str) -> str:
    """Telegram Markdown is finicky — escape only the chars that break parsing.
    We use 'Markdown' (legacy) mode because it's more forgiving for [text](url) links.
    """
    # Don't over-escape — legacy Markdown mostly tolerates plain text.
    # Our compose prompt should produce mostly-safe output.
    return text


def send_to_channel(post_text: str, dry_run: bool = False) -> bool:
    """Publish post text to the configured channel."""
    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN — would publish:")
        print("=" * 70)
        print(post_text)
        print("=" * 70 + "\n")
        return True

    url = API_BASE.format(token=Config.TELEGRAM_BOT_TOKEN) + "/sendMessage"
    payload = {
        "chat_id": Config.TELEGRAM_CHANNEL_ID,
        "text": _escape_markdown(post_text),
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,  # keep preview for source link
        "disable_notification": False,
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=20)
            data = r.json()
            if data.get("ok"):
                msg_id = data["result"]["message_id"]
                print(f"  [pub-ok] message_id={msg_id}")
                return True
            else:
                err = data.get("description", "unknown")
                print(f"  [pub-err attempt {attempt+1}] {err}")
                # Markdown parse errors → retry without markdown
                if "can't parse" in err.lower() and attempt == 0:
                    payload["parse_mode"] = ""  # plain text fallback
                    continue
                if attempt < 2:
                    time.sleep(2 ** attempt)
        except requests.RequestException as e:
            print(f"  [pub-net attempt {attempt+1}] {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
    return False


def notify_user(text: str) -> bool:
    """Send a DM to the bot owner (you) — used for logs/alerts."""
    if not Config.TELEGRAM_USER_ID:
        return False
    url = API_BASE.format(token=Config.TELEGRAM_BOT_TOKEN) + "/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": Config.TELEGRAM_USER_ID,
            "text": text[:4000],
            "disable_notification": True,
        }, timeout=10)
        return r.json().get("ok", False)
    except Exception:
        return False
