# Design Signal — AI-driven digest

Telegram channel automation: fetches RSS sources → scores with Gemini → publishes curated posts to [@design_signal](https://t.me/design_signal). Runs every 6 hours on GitHub Actions (free tier).

## Stack

- Python 3.11
- Google Gemini API (free tier: 1500 requests/day)
- Telegram Bot API
- GitHub Actions (free tier: 2000 min/month — we use ~15 min/day)

Estimated cost: **$0/month** at MVP scale.

---

## Repository structure

```
.
├── .github/workflows/digest.yml   # cron — runs every 6h
├── src/
│   ├── main.py                    # entry point
│   ├── config.py                  # env vars
│   ├── fetch.py                   # parallel RSS fetching
│   ├── score.py                   # Gemini scoring
│   ├── compose.py                 # Gemini post writing
│   ├── publish.py                 # Telegram Bot API
│   └── state.py                   # state.json (dedup)
├── prompts/
│   ├── scoring.txt
│   └── compose.txt
├── sources.yaml                   # ~60 RSS feeds
├── state.json                     # already-published URLs
├── requirements.txt
├── verify_feeds.py                # standalone feed health checker
└── .env.example
```

---

## Deployment to GitHub (10 min)

### Prerequisites
- GitHub account
- Telegram bot + channel + chat_id (see TELEGRAM_SETUP.md)
- Gemini API key from aistudio.google.com

### Step 1 — create empty repo

1. github.com → top-right `+` → **New repository**
2. Name: `design-signal`
3. Visibility: **Private** (recommended — keep code closed; state.json gets less attention)
4. ❌ Don't init with README/gitignore — we have our own
5. **Create repository**

### Step 2 — push code

In Terminal on Mac, from project folder:

```bash
cd "/Users/alexandrshemchuk/Documents/Claude/Projects/Design Digest"
git init
git add .
git commit -m "Initial Design Signal agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/design-signal.git
git push -u origin main
```

(Replace `YOUR_USERNAME` with your GitHub handle.)

If git asks for auth — use a Personal Access Token (Settings → Developer settings → PAT classic → generate token with `repo` scope) instead of password.

### Step 3 — add Secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.

Add 4 secrets:

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHANNEL_ID` | Channel chat_id (with `-100` prefix) |
| `TELEGRAM_USER_ID` | Your personal user_id (from @userinfobot) |
| `GEMINI_API_KEY` | Your Gemini key from AI Studio |

### Step 4 — first manual run

1. Repo → **Actions** tab → **Design Signal Digest** workflow → **Run workflow** → **Run workflow** (green button)
2. Wait ~2-3 min, watch the live log
3. Check your Telegram channel — first post should appear (if any article scored ≥ 8)

### Step 5 — cron is now active

GitHub Actions will run every 6h automatically. No further action needed.

---

## Local testing (optional, but recommended before push)

```bash
cd "/Users/alexandrshemchuk/Documents/Claude/Projects/Design Digest"

# Create virtual env
python3 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt python-dotenv

# Create local .env from template
cp .env.example .env
# edit .env with your real values (this file is gitignored)

# Dry run — fetches, scores, but doesn't publish
DRY_RUN=true python -m src.main

# Real run (will publish to Telegram!)
python -m src.main
```

---

## Tweaking behaviour

### Lower the publishing threshold (more posts, lower quality)
Edit `.github/workflows/digest.yml`:
```yaml
MIN_SCORE_TO_PUBLISH: '7'   # was 8
```

### Post more frequently
Edit cron in same file:
```yaml
- cron: '0 */3 * * *'   # every 3 hours
```

### Add/remove sources
Edit `sources.yaml`. Run `verify_feeds.py` after to validate.

### Adjust voice / prompt
Edit `prompts/compose.txt` and `prompts/scoring.txt`. No code change needed.

---

## Monitoring

- **GitHub Actions tab** — see each run's log
- **Telegram DM to bot** — agent sends you summaries: "Published 2 posts" or "0 publishable items"
- **State file** — `state.json` shows everything ever published

---

## Cost tracking

Gemini free tier limits:
- 1500 requests/day total
- 15 requests/minute

Our usage at 4 runs/day:
- ~50-80 scoring calls per run × 4 = 200-320/day (well within 1500)
- ~1-3 compose calls per run × 4 = 4-12/day

If you hit limits → switch to paid tier ($0.0001 per call ≈ $1/month at our scale) or switch to Claude (uncomment `ANTHROPIC_API_KEY` in `.env.example` and update code).

---

## Troubleshooting

**"can't parse entities"** in Telegram log
→ Markdown in post broke. The publisher auto-retries in plain text. If frequent, soften the compose prompt.

**Gemini 429 rate limit**
→ You hit 15 RPM. Reduce `MAX_TO_SCORE_PER_RUN` in `src/main.py` or run less often.

**Nothing publishes for several runs**
→ Threshold too high. Lower `MIN_SCORE_TO_PUBLISH` to 7, observe quality, adjust.

**Bot says "Chat not found"**
→ chat_id wrong. Re-check via API URL trick in TELEGRAM_SETUP.md.
