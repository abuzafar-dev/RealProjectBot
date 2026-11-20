claude# RealProjectBot — Vazifalar boti

[![CI](https://github.com/abuzafar-dev/RealProjectBot/actions/workflows/ci.yml/badge.svg)](https://github.com/abuzafar-dev/RealProjectBot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.31-2CA5E0)

Telegram uchun shaxsiy vazifalar (todo) boti. Foydalanuvchi vazifa qo'shadi, ro'yxatini ko'radi,
bajarilganini belgilaydi, o'chiradi va o'z statistikasini kuzatadi.

## Imkoniyatlar

- **Vazifa qo'shish** — FSM orqali; nom bo'sh yoki 200 belgidan uzun bo'lsa rad etiladi,
  ortiqcha bo'sh joylar tozalanadi
- **Vazifalar ro'yxati** — bitta xabarda, sahifalarga bo'lingan (10 tadan, ◀️ ▶️).
  Bajarilmaganlar tepada, bajarilganlar ~~ustidan chizilgan~~
- **✅ Bajarildi / 🗑 O'chirish** — inline tugmalar; ro'yxat o'sha xabarning o'zida yangilanadi
- **📊 Statistika** — jami, bajarilgan, qolgan va progress bar
- `/start`, `/help`, `/cancel` buyruqlari, Telegram menyusida ko'rinadi
- Har bir foydalanuvchi faqat **o'z** vazifalarini ko'radi va o'zgartira oladi

## Texnologiyalar

| | |
|---|---|
| Bot freymvorki | [aiogram 3](https://docs.aiogram.dev) (asinxron) |
| Ma'lumotlar bazasi | SQLite + [aiosqlite](https://github.com/omnilib/aiosqlite) |
| Testlar | pytest + pytest-asyncio |
| Linter / formatter | [ruff](https://docs.astral.sh/ruff/) |
| Deploy | Docker, docker compose |
| CI | GitHub Actions — har bir push'da lint va testlar |

## Arxitektura

```
main.py                 kirish nuqtasi: sozlamalar, baza, Dispatcher, polling, to'xtash
bot/
  config.py             .env ni o'qish va tekshirish (Settings)
  database.py           Database klassi, Task/Stats modellari, sxema va migratsiya
  keyboards.py          reply va inline tugmalar, CallbackData
  states.py             FSM holatlari
  handlers/
    start.py            /start, /help, /cancel, statistika
    tasks.py            vazifa qo'shish, ro'yxat, sahifalash, callbacklar
    errors.py           global xato ushlagich
tests/                  baza va handlerlar uchun testlar
scripts/ci.sh           lokal va CI'da bir xil tekshiruv
```

**Muhim qarorlar:**

- **Dependency injection.** `Database` obyekti `Dispatcher(db=db)` orqali beriladi va aiogram
  uni handlerlarga argument sifatida uzatadi. Global o'zgaruvchi yo'q, shuning uchun testlarda
  har bir test o'zining toza bazasini oladi.
- **Asinxron baza.** `aiosqlite` so'rovlarni alohida thread'da bajaradi, shuning uchun bitta
  foydalanuvchining so'rovi boshqalarni kutib turmaydi (event loop bloklanmaydi).
- **Xavfsizlik.** Har bir `UPDATE`/`DELETE` so'rovida `user_id` sharti bor, ya'ni callback
  ma'lumotini soxtalashtirib boshqa birovning vazifasiga tegib bo'lmaydi. Barcha SQL so'rovlar
  parametrli (SQL injection yo'q), foydalanuvchi matni `html.quote` bilan chiqariladi.
- **Bitta xabarli ro'yxat.** Har bir vazifani alohida xabar qilib yuborish ko'p vazifada
  Telegram flood limitiga uriladi. Shuning uchun ro'yxat bitta xabarda sahifalab ko'rsatiladi
  va tugma bosilganda `edit_text` bilan yangilanadi.
- **Migratsiya.** Eski bazada yangi ustun (`done_at`) bo'lmasa, ishga tushishda avtomatik
  qo'shiladi. Ma'lumotlar yo'qolmaydi.

## Ishga tushirish

Avval [@BotFather](https://t.me/BotFather) dan token oling.

```bash
make run      # .venv va .env yaratadi, kutubxonalarni o'rnatadi, botni ishga tushiradi
```

Birinchi marta `make run` `.env` faylini yaratadi. Ichiga `BOT_TOKEN=...` ni yozib, qayta ishga tushiring.

<details><summary>make'siz</summary>

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # BOT_TOKEN ni yozing
python main.py
```
</details>

### Sozlamalar (`.env`)

| O'zgaruvchi | Majburiy | Standart | Tavsif |
|---|---|---|---|
| `BOT_TOKEN` | ha | — | @BotFather bergan token |
| `DB_PATH` | yo'q | `tasks.db` | SQLite fayl yo'li |
| `LOG_LEVEL` | yo'q | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Docker

```bash
make docker-up      # docker compose up --build -d
make docker-logs
make docker-down
```

Konteyner root bo'lmagan foydalanuvchida ishlaydi va image'ga faqat production kutubxonalari
tushadi. Baza `bot_data` volume'da saqlanadi, shuning uchun konteyner qayta yaratilsa ham
vazifalar yo'qolmaydi.

## Testlar va sifat

```bash
make test     # ruff lint + format tekshiruvi + pytest (CI bilan aynan bir xil)
make format   # kodni avtomatik formatlash
```

Testlar quyidagilarni qamraydi: bazaning CRUD amallari, saralash va sahifalash, boshqa
foydalanuvchi vazifasiga kirishni taqiqlash, foreign key, eski sxemadan migratsiya, vazifa
qo'shish validatsiyasi, HTML escaping, ro'yxat va sahifa tugmalari, callbacklar, statistika.
