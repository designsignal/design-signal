# Telegram Setup — AI Native Product Design

Step-by-step інструкція. Підходить і для desktop, і для mobile (Telegram має майже ідентичний UI). Загальний час: ~30 хвилин.

## Що отримаєш у результаті

- Публічний канал з reactions, коментарями і обговореннями
- Discussion group, де читачі обговорюють пости
- Bot з токеном для AI-агента
- Збережені credentials для GitHub Secrets

---

## Крок 1: Створити канал (5 хв)

### Mobile (iOS/Android):
1. Відкрий Telegram → натисни значок ✏️ (нове повідомлення) у правому верхньому куті
2. **New Channel**
3. Заповни:
   - **Channel name:** `AI Native Product Design`
   - **Description:** скопіюй з шаблону нижче
   - **Photo:** залий аватарку (поки можеш просту з літерою "A", потім поміняєш)
4. **Channel Type:** обери **Public Channel**
5. **Permanent link:** введи handle. Спробуй по черзі:
   - `ainativedesign`
   - `ai_native_design`
   - `ainativeproduct`
   - `ainative_pd`
   - Якщо всі зайняті — додай суфікс `_ua` (`ainativedesign_ua`)
6. **Add Subscribers:** натисни **Skip** (додаси пізніше)
7. Канал створено ✓

### Desktop (macOS/Windows):
1. Telegram Desktop → натисни ✏️ (олівець у правому куті списку чатів)
2. **New Channel** → далі ідентично mobile

### Шаблон опису (250 символів макс)
```
Щоденний потік AI-driven дизайну: Lovable, v0, Figma AI, Cursor, Claude, Stitch.
Інструменти, агенти, workflow.
Українською, з посиланнями на оригінал.
Куратор: Олександр Шемчук → @твій_нік
```

---

## Крок 2: Налаштувати канал ПРАВИЛЬНО (10 хв) ⚠️ Критичний крок

Це те, що потім складно змінювати або через що люди йдуть. Зроби зразу.

Зайди в канал → натисни на назву зверху → **Edit** (олівець або три крапки → Manage Channel).

### Channel Info
- **Channel Photo:** залий якісний аватар (1024×1024 px, прозорий PNG)
- **Channel Name:** перевір
- **Description:** перевір

### Reactions ⚠️ обов'язково
- **Reactions → Enable**
- Обери **All Reactions** (не Some) — щоб люди могли реагувати будь-яким емоджи
- **Custom emoji from Premium:** Enable
- Це збільшує engagement в 2-3 рази

### Channel Type
- **Public Channel** ✓
- **Restrict Saving Content:** OFF (вимкнено) — щоб люди могли пересилати твої пости, це безкоштовний маркетинг

### Sign Messages
- За бажанням. Якщо ON — внизу кожного посту буде ім'я адміна, який запостив.
- Для AI-керованого каналу краще **OFF** (нехай виглядає як єдиний голос каналу)

### Auto-Delete Messages
- **OFF** ⚠️ (інакше твій архів самознищиться)

### Slow Mode (для каналу)
- N/A для каналу

---

## Крок 3: Створити Discussion Group (5 хв)

Discussion group — це окрема група, до якої прив'язується канал. Коли хтось коментує пост — коментар з'являється в групі. Без цього коментарів не буде.

### Найпростіший шлях (рекомендую):
1. У налаштуваннях каналу → **Discussion** → **Create New Group**
2. Telegram сам створить групу і одразу прив'яже її до каналу
3. Назва групи (автопропозиція): `AI Native Product Design Chat` — підтверди або зміни на щось коротке типу `AI Design Chat`
4. Тип групи: **Public** ✓ (інакше нові читачі не зможуть приєднатися)
5. Handle групи: `ainativedesign_chat` (або похідне)

### Налаштування групи (важливо!)
Зайди в групу → назва зверху → Edit → **Permissions**:

| Дозвіл | Стан | Чому |
|--------|------|------|
| Send Messages | ✅ ON | Інакше нащо група |
| Send Media | ✅ ON | Скріни, відео — основа дизайн-обговорень |
| Send Stickers & GIFs | ✅ ON | Engagement |
| Embed Links | ✅ ON | Щоб люди ділилися джерелами |
| Send Polls | ✅ ON | Корисно для опитувань |
| Add Members | ❌ OFF | Захист від спам-армій, які тебе у свій канал додадуть |
| Pin Messages | ❌ OFF | Тільки адмін |
| Change Group Info | ❌ OFF | Тільки адмін |

**Slow Mode:** залиш **OFF** на старті. Увімкнеш (15s або 30s), якщо почнеться флуд.

**Topics (Forum mode):** залиш **OFF** на старті. Увімкнеш потім, коли буде > 1000 учасників і логічно розділити обговорення.

---

## Крок 4: Створити бота через @BotFather (5 хв)

Це бот, який буде публікувати від твого імені.

### Створення:
1. У пошуку Telegram знайди **@BotFather** (з блакитною галочкою — оригінал)
2. /start
3. /newbot
4. Введи display name: `AI Native Design Bot`
5. Введи username: `ainative_design_bot` (має закінчуватися на `bot`)
6. **ЗБЕРЕЖИ TOKEN** — це довгий рядок типу `7123456789:AAH...`. Він буде у тебе тільки раз показаний. Це твій ключ доступу — не діли ні з ким.

### Налаштування бота (одразу, поки не забув):
У чаті з @BotFather:
- `/setdescription` → обери свого бота → введи `Публікує дайджест AI Native Product Design`
- `/setabouttext` → обери бота → введи `Bot for AI Native Product Design channel. Куратор: Олександр Шемчук.`
- `/setuserpic` → обери бота → залий ту саму аватарку, що й у каналу
- `/setprivacy` → обери бота → **Disable** ⚠️ (інакше бот не зможе читати повідомлення в групі — це знадобиться для safety-gate)
- `/setjoingroups` → **Enable** (щоб бот міг приєднатися до твоєї discussion group)

---

## Крок 5: Додати бота як адміна (3 хв) ⚠️ В обидва місця

### У канал:
1. Канал → назва зверху → **Administrators** → **Add Administrator**
2. Знайди свого бота за username (`@ainative_design_bot`)
3. Постав permissions:
   - ✅ Post Messages (основне)
   - ✅ Edit Messages of Others
   - ✅ Delete Messages of Others
   - ✅ Pin Messages
   - ❌ Add New Admins (security — щоб бот не міг сам додавати інших ботів)
   - ❌ Remain Anonymous (хай буде видно, що він пише — це нормально)
4. **Done**

### У discussion group:
1. Група → назва зверху → **Administrators** → **Add Administrator**
2. Знайди того ж бота
3. Permissions:
   - ✅ Delete Messages (модерація)
   - ✅ Ban Users (захист від спаму)
   - ✅ Pin Messages
   - ❌ Add New Admins
4. **Done**

⚠️ **Без цього кроку бот нічого не запостить** — Telegram вимагає admin-прав.

---

## Крок 6: Отримати chat_id каналу і групи (2 хв)

Бот треба знати, куди постити. Йому передаються chat_id (це не username, а цифровий ID).

### Спосіб 1 (через @userinfobot — найпростіший):
1. У каналі опублікуй тестовий пост (наприклад "тест")
2. Затисни на ньому → **Forward** → знайди **@userinfobot**
3. @userinfobot відповість приблизно: `Forwarded from chat: AI Native Product Design, chat ID: -1002123456789`
4. **Збережи цей chat_id** (з мінусом!)
5. Те саме для discussion group — напиши тест у групі, переслай @userinfobot

### Спосіб 2 (якщо @userinfobot не працює):
Знайди в Telegram бота `@RawDataBot` або `@JsonDumpBot` — переслати йому повідомлення, він дасть JSON з полем `chat.id`.

---

## Крок 7: Save credentials (1 хв)

Створи у себе на комп'ютері заметку (або повідомлення Saved Messages у Telegram, чи 1Password) з такими полями:

```
=== AI Native Product Design — Telegram Credentials ===

Channel handle:      @ainativedesign
Channel chat_id:     -1002XXXXXXXXXX
Channel URL:         https://t.me/ainativedesign

Group handle:        @ainativedesign_chat
Group chat_id:       -1002YYYYYYYYYY
Group URL:           https://t.me/ainativedesign_chat

Bot username:        @ainative_design_bot
Bot TOKEN:           7XXXXXXXXX:AAH... (ВЕЛИЧЕЗНИЙ СЕКРЕТ)

Your Telegram user_id (для safety-gate): ZZZZZZZZ
(дізнайся: напиши /start боту @userinfobot — він покаже)
```

⚠️ **Bot TOKEN ніколи не публікуй у git, не показуй на скрінах, не вставляй у код напряму.** Він йде тільки в GitHub Secrets (наступний крок при створенні агента).

---

## Що відправити мені, коли все готово

Просто напиши:
1. ✅ Канал створено: `@handle`
2. ✅ Група створена і прив'язана: `@group_handle`
3. ✅ Бот створено: `@bot_username`
4. ✅ Chat IDs отримані (мені пиши, я допоможу з кодом — токен НЕ пиши в чат)
5. ✅ Бот доданий як admin у канал і групу

Після цього переходимо до коду агента — і за пару годин у тебе працюючий MVP.

---

## Чек-лист "все працює правильно"

Перш ніж рухатися далі, переконайся:

- [ ] У канал можна зайти за публічним посиланням `https://t.me/handle`
- [ ] Під своїм тестовим постом видно кнопку **Comments**
- [ ] Натискаючи Comments — відкривається discussion group, можна писати коментар
- [ ] Під постом можна поставити реакцію (тримай на пості → з'являється палітра емоджи)
- [ ] Бот видно у списку адмінів каналу і групи
- [ ] Bot TOKEN збережено у безпечному місці

Якщо щось з цього не працює — напиши, розберемося.
