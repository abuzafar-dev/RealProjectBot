# RealProjectBot — eslatuvchi vazifalar boti

[![CI](https://github.com/abuzafar-dev/RealProjectBot/actions/workflows/ci.yml/badge.svg)](https://github.com/abuzafar-dev/RealProjectBot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.31-2CA5E0)

Vazifalarni yozib qo'yib, **vaqti kelganda o'zi eslatadigan** shaxsiy Telegram bot.

## Muammo

Men ishlarni yozib qo'yaman, lekin baribir unutaman. Sabab — eslatma yo'qligi:

- **Odatiy todo ilovalari passiv.** Ular faqat ochganingizda foyda beradi. Band kunda ilovani
  ochish esdan chiqadi, demak ro'yxat ham, muddat ham esdan chiqadi.
- **Qog'oz, "Saved Messages", eslatmalar** — tartib yo'q: nima bajarildi, nimaning muddati
  o'tdi, bugun nima qilish kerak — bir qarashda ko'rinmaydi.
- **Telefon budilniklari** har bir ish uchun alohida sozlanadi, ro'yxat va statistika bermaydi.

Natija: muddat o'tib ketgandan keyin eslanadi.

## Yechim

Telegram — kun bo'yi baribir ochiq turadigan ilova. Shuning uchun vazifalar ro'yxati o'sha yerda,
eng muhimi esa — **bot o'zi yozadi**, uni ochish shart emas:

| Muammo | Botdagi yechim |
|---|---|
| Muhim ishni aniq vaqtda unutaman | `ertaga 15:00` deb yozilsa — aynan 15:00 da ⏰ eslatma, ichida ✅ tugma |
| Bugun nima qilishim kerakligini bilmayman | Har kuni ertalab (08:00) ☀️ **bugungi reja** va muddati o'tganlar |
| Ro'yxat chalkash | Eng yaqin muddat tepada, ⚠️ muddati o'tganlar belgilangan, bajarilganlar ~~chizilgan~~ |
| Qancha ish qildim — ko'rinmaydi | 📊 statistika: jami, bajarilgan, qolgan, muddati o'tgan, progress |
| Ilova o'rnatish, ro'yxatdan o'tish | Kerak emas — `/start` bosiladi, tamom |

**Nega aynan shunday, murakkabroq emas:**

- **Ikki xil eslatma — yetarli va sodda.** Vaqtli ish (uchrashuv, qo'ng'iroq) aniq vaqtda kerak;
  vaqtsiz ish (hisobot, uy ishi) esa shu kun ertalab ko'rinsa bas. Takrorlanuvchi eslatmalar,
  kategoriyalar, ustuvorlik — bitta odamga ortiqcha murakkablik, shuning uchun qo'shilmadi.
- **Muddat ixtiyoriy.** `⏭ Muddatsiz` tugmasi bilan oddiy ro'yxat sifatida ham ishlatish mumkin.
- **Spam yo'q.** Ertalabki reja faqat bugungi yoki muddati o'tgan ish bo'lsa keladi, kuniga bir marta.
- **Yangi kutubxona/servis yo'q.** Eslatmalar bot ichidagi fon vazifasi (30 soniyada bir tekshiruv),
  Redis, Celery yoki alohida scheduler kerak emas.

## Imkoniyatlar

- **Vazifa qo'shish** — 2 qadam: nom → muddat. Nom bo'sh yoki 200 belgidan uzun bo'lsa rad
  etiladi. Muddat: `bugun`, `ertaga`, `25.11`, `25.11.2026`, `ertaga 15:00`, `18:30` yoki tugmalar.
  O'tib ketgan sana/vaqt va mavjud bo'lmagan sana (`31.02`) qabul qilinmaydi
- **⏰ Eslatma** — vaqtli vazifa uchun aniq vaqtda, xabardagi **✅ Bajarildi** tugmasi bilan
- **☀️ Ertalabki reja** — bugungi va muddati o'tgan vazifalar, kuniga bir marta
- **Vazifalar ro'yxati** — bitta xabarda, sahifalarga bo'lingan (10 tadan, ◀️ ▶️)
- **✅ Bajarildi / 🗑 O'chirish** — inline tugmalar; ro'yxat o'sha xabarning o'zida yangilanadi
- **📊 Statistika** — jami, bajarilgan, qolgan, muddati o'tgan va progress bar
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
main.py                 kirish nuqtasi: sozlamalar, baza, Dispatcher, eslatmalar, polling
bot/
  config.py             .env ni o'qish va tekshirish (Settings)
  database.py           Database klassi, Task/Stats modellari, sxema va migratsiya
  due.py                muddat matnini o'qish va ko'rsatish (sof funksiyalar)
  reminders.py          eslatmalar va ertalabki reja (fon vazifasi)
  clock.py              vaqt zonasidagi joriy vaqt (testda qotiriladi)
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
- **Eslatma ikki marta kelmaydi va yo'qolmaydi.** Har bir yuborish bazada belgilanadi
  (`tasks.reminded`, `users.last_digest`). Bot o'chiq turganda vaqti o'tgan eslatma ishga
  tushishi bilan yuboriladi; qayta ishga tushirish takroriy xabar bermaydi. Telegram vaqtincha
  ishlamasa, eslatma belgilanmaydi va keyingi tekshiruvda qayta yuboriladi. Botni bloklagan
  foydalanuvchi boshqalarga eslatma yetishini to'xtatmaydi.
- **Vaqt — dependency.** Joriy vaqt `Clock` obyekti orqali olinadi, shuning uchun testlarda
  "hozir"ni qotirib, eslatmalarni soatni kutmasdan tekshirish mumkin.
- **Migratsiya.** Eski bazada yangi ustunlar (`done_at`, `due_date`, `due_time`, `reminded`,
  `last_digest`) bo'lmasa, ishga tushishda avtomatik qo'shiladi. Ma'lumotlar yo'qolmaydi.

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
| `TIMEZONE` | yo'q | `Asia/Tashkent` | eslatmalar vaqt zonasi |
| `DIGEST_HOUR` | yo'q | `8` | ertalabki reja soati (0..23) |

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

49 ta test quyidagilarni qamraydi: bazaning CRUD amallari, muddat bo'yicha saralash va
sahifalash, boshqa foydalanuvchi vazifasiga kirishni taqiqlash, foreign key, eski sxemadan
migratsiya, muddat matnini o'qish (to'g'ri va noto'g'ri formatlar), vazifa qo'shish oqimi,
HTML escaping, ro'yxat va callbacklar, statistika, eslatmaning aniq vaqtda va faqat bir marta
kelishi, o'tib ketgan eslatma, ertalabki reja (kuniga bir marta, bo'sh bo'lsa yuborilmaydi),
botni bloklagan foydalanuvchi.
