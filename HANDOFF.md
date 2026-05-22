# Design Signal — Project Handoff

> Цей документ описує проект так, щоб ти (Alex, продакт-дизайнер, не програміст) міг **продовжити роботу через будь-якого AI агента** (Claude, ChatGPT, Cursor, тощо) без втрати контексту.
> 
> **Якщо ти AI агент, який читає цей файл вперше — прочитай повністю перш ніж вносити зміни. Цей файл містить весь контекст, який тобі потрібен.**

---

## 1. Що це за проект

**Design Signal** — автоматичний україномовний Telegram-канал [@design_signal](https://t.me/design_signal) про AI-дизайн та AI-інструменти для білдерів.

**Аудиторія:** українські продакт-дизайнери mid-senior рівня, які користуються AI-інструментами (Figma, Lovable, v0, Cursor, Claude, ChatGPT) щодня.

**Як працює:** GitHub Actions запускає Python-агента за розкладом. Агент:
1. Збирає статті з RSS-фідів (`sources.yaml`)
2. Оцінює їх Claude Haiku 4.5 (швидко й дешево)
3. Найкращі (score ≥ 6) — переписує українською через Claude Sonnet 4.6
4. Постить у Telegram через Bot API

**Філософія:** zero-touch. Жодних ручних дій від тебе після первинного налаштування.

---

## 2. Поточний стан (на 22 травня 2026)

| Що | Статус |
|---|---|
| Канал створений | ✅ [@design_signal](https://t.me/design_signal) |
| Бот налаштований (admin рівень) | ✅ |
| GitHub репо | ✅ public — `github.com/designsignal/design-signal` |
| GitHub Actions workflow | ✅ запускається щогодини на `:57 UTC` |
| Anthropic API ключ | ✅ збережено в GitHub Secrets |
| Перший пост опубліковано | ✅ ("Агенти хочуть не пісочниці...") |
| Outage-recovery логіка | ✅ retry через 10 хв якщо Anthropic 529 |
| Тестовий режим | ⏳ зараз щогодини, потім → 09:30 Київ |
| Зламані RSS-фіди (22/53) | ⏳ deferred — фіксити коли стабілізуємось |

---

## 3. Структура файлів (плейн англійською для AI)

```
design-signal/
├── .github/workflows/digest.yml    # GitHub Actions: cron schedule + env vars + run command
├── src/
│   ├── main.py                     # Orchestrator: fetch → dedupe → score → compose → publish
│   ├── fetch.py                    # RSS feed parser (feedparser)
│   ├── score.py                    # Claude Haiku scorer + outage-recovery retry logic
│   ├── compose.py                  # Claude Sonnet post composer (Ukrainian)
│   ├── publish.py                  # Telegram Bot API client + notify_user (DM alerts)
│   ├── state.py                    # SHA-256 URL dedup via state.json
│   └── config.py                   # Env vars loader (TELEGRAM_*, ANTHROPIC_API_KEY)
├── prompts/
│   ├── scoring.txt                 # Haiku prompt: bell curve at 6, AI/builder rubric
│   └── composing.txt               # Sonnet prompt: Ukrainian voice, format, length
├── sources.yaml                    # RSS feed list with tags/weights
├── state.json                      # Auto-updated dedup state (URL hashes seen)
├── requirements.txt                # anthropic==0.40.0, feedparser, requests, pyyaml
└── HANDOFF.md                      # This file
```

---

## 4. Як це працює (data flow)

```
GitHub Actions cron ('57 * * * *' UTC)
        ↓
  src/main.py
        ↓
  1. fetch.py: pull all RSS feeds from sources.yaml
  2. state.py: filter out previously-seen URLs (SHA-256 hash)
  3. filter: keep only articles published in last 3 days
  4. per-source cap: max 2 articles per source (prevents arXiv flooding)
  5. sort by recency, take top 15
        ↓
  6. score.py: Haiku rates each 0-10 (with weight adjustment)
     - On 529 overload: 3 retries with 20s/45s/90s backoff + jitter
     - If 33%+ fail: sleep 10 min, retry failed only
     - If still failing: DM owner via notify_user, give up gracefully
        ↓
  7. filter: keep score ≥ MIN_SCORE_TO_PUBLISH (currently 6)
  8. take top MAX_POSTS_PER_RUN (currently 3)
        ↓
  9. compose.py: Sonnet writes Ukrainian post for each
 10. publish.py: send to @design_signal via Telegram Bot API
        ↓
 11. state.json updated with new URL hashes
 12. GitHub Actions auto-commits state.json (no infinite loop — [skip ci])
```

---

## 5. Де живуть секрети

**ЖОДЕН секрет ніколи не в коді або в чаті.** Усі — у GitHub Secrets (`Settings → Secrets and variables → Actions`):

| Secret name | Що це | Якщо втратив |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота `@design_signal_bot` | Йди в [@BotFather](https://t.me/BotFather) → `/mybots` → revoke + новий токен |
| `TELEGRAM_CHANNEL_ID` | `@design_signal` (username каналу) | Не змінюється |
| `TELEGRAM_USER_ID` | Твій chat_id для DM-алертів | Отримай через [@userinfobot](https://t.me/userinfobot) |
| `ANTHROPIC_API_KEY` | sk-ant-... API ключ | [console.anthropic.com](https://console.anthropic.com) → API Keys → revoke + новий |

**Важливо:** Anthropic API ключ створено на **особистому email і особистій картці**, окремо від робочого `o.shemchuk@retouchme.com`. Це навмисно — щоб біллинг каналу не змішувався з корпоративним.

---

## 6. Як змінювати налаштування (без коду)

### Поріг публікації, частота, ліміти
Файл: `.github/workflows/digest.yml` → секція `env:`

```yaml
MIN_SCORE_TO_PUBLISH: '6'      # підняти до 7 для строгішого фільтра
MAX_POSTS_PER_RUN: '3'          # скільки максимум постів за один запуск
DRY_RUN: 'false'                # 'true' = тільки логи, нічого не публікувати
```

### Розклад запуску
Той самий файл, верх:

```yaml
- cron: '57 * * * *'         # зараз: щогодини на :57 UTC (для тестування)
# - cron: '30 6 * * *'       # production: 09:30 Київ (літо UTC+3)
```

[Cron generator](https://crontab.guru) допоможе якщо треба інший час.

### Джерела новин
Файл: `sources.yaml`. Формат:

```yaml
- name: Lovable Blog
  url: https://lovable.dev/feed.xml
  tags: [ai-tools, builders]
  weight: 1.0          # 0.0-1.0, впливає на фінальну оцінку
  enabled: true        # false = тимчасово вимкнути
```

### Тон/стиль постів
Файл: `prompts/composing.txt` — інструкція для Sonnet як писати українською.

### Критерії оцінки
Файл: `prompts/scoring.txt` — рубрика для Haiku (що "цінне", що "ні").

---

## 7. Відомі обмеження

1. **22 з 53 RSS-фідів не парсяться** — Cursor, Lovable, v0, Anthropic, Figma, Linear повертають HTML замість XML або malformed XML. Не критично (ми отримуємо новини про них через інші джерела), але треба колись пофіксити через скрапінг.
2. **GitHub Actions free tier throttling** — scheduled runs можуть скіпатись при високому навантаженні. Тому використовуємо off-peak хвилину `:57` (не `:00`).
3. **Anthropic періодично перевантажений (529)** — обробляємо graceful через retry + DM, але іноді цілий run буде fail. Наступний cron вирівняє.
4. **Дублювання поста в discussion group** — це нормальна поведінка Telegram (каналу з прив'язаним чатом). Не баг.

---

## 8. Як передати проект новому AI агенту

Скопіюй наступний промпт у новий чат з будь-яким AI:

```
Я Alex, продакт-дизайнер, не програміст. Я веду автоматичний україномовний 
Telegram-канал @design_signal про AI-дизайн.

Репо: https://github.com/designsignal/design-signal (публічний)
Локальна папка: ~/Documents/Claude/Projects/Design Digest

Перш ніж щось робити, прочитай HANDOFF.md в корені проекту — там повний контекст.
Усі секрети живуть в GitHub Secrets, я ніколи їх не показую в чаті.

Я хочу: [тут опиши що тобі треба]
```

**Поради як працювати з новим AI:**
- Скажи що ти **не програміст** — тоді AI пояснюватиме простіше
- Завжди проси AI пояснити що він збирається зробити **до** того як робити
- Не показуй секрети (токени, API ключі) у чаті навіть якщо AI просить
- Якщо AI пропонує закомітити в репо щось чутливе — зупини його
- Кожна зміна → `git add`, `commit`, `push` → перевірка в GitHub Actions

---

## 9. Витрати

- **Anthropic API:** ~$4/місяць (Haiku scoring + Sonnet composing, ~40 статей/день)
- **GitHub:** 0 (репо публічний → unlimited Actions minutes)
- **Telegram Bot API:** 0
- **Domain/hosting:** 0

Бюджет в Anthropic Console: $20 поповнено, вистачить на ~5 місяців.

---

## 10. Майбутні задачі (roadmap)

### Найближчі
- [ ] Перевірити що cron надійно запускається на публічному репо (зараз тестуємо)
- [ ] Коли все стабільне → повернути на щоденний `'30 6 * * *'` (09:30 Київ)
- [ ] Опустити `MAX_POSTS_PER_RUN` назад до 2 для production
- [ ] Пофіксити 22 зламані RSS-фіди (написати fallback parser або замінити на скрапінг)

### V2 (коли MVP стабільний)
- [ ] Safety kill-switch — змінна в GitHub Secrets для миттєвого зупину публікацій
- [ ] Тематична категоризація постів (`#tools`, `#models`, `#agents`)
- [ ] Невелика "ранкова добірка" на тиждень-back замість окремих постів
- [ ] Seed аудиторії — анонс в LinkedIn, дизайнерських чатах

### Контент
- [ ] Описати канал коротко в Telegram bio
- [ ] Обкладинка/іконка каналу (можна згенерувати в Figma або через AI)
- [ ] Pinned-пост зі статусом проекту (для перших підписників)

---

## 11. Глосарій (для не-програміста)

- **GitHub Actions** — безкоштовний сервер GitHub який запускає твій код за розкладом
- **Cron** — формат розкладу типу `'30 6 * * *'` означає "о 6:30 ранку щодня"
- **Secret** — захищена змінна в GitHub яка не видна в коді (для токенів)
- **Workflow** — описаний в YAML-файлі сценарій що робить GitHub Actions
- **Repo (repository)** — папка з проектом на GitHub
- **Push** — відправити локальні зміни на GitHub
- **Pull** — забрати свіжі зміни з GitHub
- **Commit** — зберегти знімок змін з повідомленням про те що змінилось
- **RSS** — формат стрічки новин що публікують більшість блогів
- **API** — спосіб двом програмам спілкуватись (Telegram API, Anthropic API)
- **529 error** — Anthropic перевантажений, треба зачекати
- **Dry run** — запустити без реальних побічних ефектів (нічого не публікувати, тільки логи)

---

## 12. Контакти / посилання

- **Канал:** [@design_signal](https://t.me/design_signal)
- **GitHub:** [github.com/designsignal/design-signal](https://github.com/designsignal/design-signal)
- **Anthropic Console:** [console.anthropic.com](https://console.anthropic.com)
- **BotFather:** [@BotFather](https://t.me/BotFather) (керування ботом)
- **Crontab guru:** [crontab.guru](https://crontab.guru) (cron expressions)

---

_Останнє оновлення: 22 травня 2026, після того як проект став публічним і cron перенесли на `:57`._
