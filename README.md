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
| Eslatma noqulay paytda keldi | ⏰ **+15 daq / +1 soat / Ertaga** — bir bosishda kechiktiriladi va qayta keladi |
| Har kungi odatlar (sport, dori, kitob) | `har kuni 09:00`, `har hafta` — 🔁 bajarilganda keyingisi o'zi yaratiladi |
| Bugun nima qilishim kerakligini bilmayman | Har kuni ertalab (08:00) ☀️ **bugungi reja**, istalgan payt — «☀️ Bugungi reja» |
| Yozish uchun ko'p qadam | Bitta xabar kifoya: `Hisobot ertaga 15:00` — nom va muddat o'zi ajratiladi |
| Har kimning kuni har xil boshlanadi | ⚙️ Sozlamalarda ertalabki reja soati (06:00–10:00) shaxsan tanlanadi |
| Qancha ish qilganim sezilmaydi | 📈 Har yakshanba haftalik hisobot, 📊 da 🔥 ketma-ket kunlar |
| Ro'yxat chalkash | Eng yaqin muddat tepada, ⚠️ muddati o'tganlar belgilangan, bajarilganlar ~~chizilgan~~ |
| Qancha ish qildim — ko'rinmaydi | 📊 statistika: jami, bajarilgan, qolgan, muddati o'tgan, progress |
| Ilova o'rnatish, ro'yxatdan o'tish | Kerak emas — `/start` bosiladi, tamom |

**Nega aynan shunday, murakkabroq emas:**

- **Ikki xil eslatma — yetarli va sodda.** Vaqtli ish (uchrashuv, qo'ng'iroq) aniq vaqtda kerak;
  vaqtsiz ish (hisobot, uy ishi) esa shu kun ertalab ko'rinsa bas.
- **Takrorlanish — faqat kunlik va haftalik.** Botni real ishlatganda eng ko'p kerak bo'lgani shu
  ikkisi bo'ldi (odatlar). Takrorlanuvchi vazifa bitta yozuv bo'lib turadi; bajarilganda keyingi
  sanasi bilan yangisi yaratiladi, shuning uchun bajarilganlar tarixi va statistika buzilmaydi.
  Bir necha kun o'tkazib yuborilsa ham keyingisi o'tmishda emas, kelajakda yaratiladi.
  Kategoriyalar, ustuvorlik, cron-ifodalar — bitta odamga ortiqcha murakkablik, qo'shilmadi.
- **Muddat ixtiyoriy.** `⏭ Muddatsiz` tugmasi bilan oddiy ro'yxat sifatida ham ishlatish mumkin.
- **Spam yo'q.** Ertalabki reja faqat bugungi yoki muddati o'tgan ish bo'lsa keladi, kuniga bir marta.
- **Yangi kutubxona/servis yo'q.** Eslatmalar bot ichidagi fon vazifasi (30 soniyada bir tekshiruv),
  Redis, Celery yoki alohida scheduler kerak emas.

## Imkoniyatlar

- **Birinchi tanishuv** — Start bosilishidan oldin bo'sh chatda bot nima qila olishi yozilgan
  tavsif ko'rinadi (bot ishga tushganda Telegram'ga avtomatik yoziladi). `/start` dan keyin
  rasm va 3 qadamli qisqa yo'riqnoma keladi
- **Vazifa qo'shish** — 3 qadam: nom → qaysi kun → soat nechada eslatish. Oxirida bot
  eslatma **qachon** kelishini aniq yozadi. Bugun uchun faqat hali kelmagan soatlar taklif
  qilinadi; «☀️ Ertalabki rejada» faqat o'sha reja haqiqatan yuboriladigan bo'lsa ko'rsatiladi —
  shuning uchun eslatmasi hech qachon kelmaydigan vazifa yaratib bo'lmaydi.
  `ertaga 15:00` deb bir yo'la yozish ham mumkin. Menyusiz ham: istalgan matnni yozib yuborsangiz,
  u vazifa nomi bo'ladi. Nom 3 belgidan qisqa, harfsiz (`123`, `...`), 200 belgidan uzun yoki menyu tugmasi bo'lsa rad etiladi.
  Muddat: `bugun`, `ertaga`, `25.11`, `25.11.2026`, `ertaga 15:00`, `18:30`, `har kuni 09:00`,
  `har hafta` yoki tugmalar. O'tib ketgan sana/vaqt va mavjud bo'lmagan sana (`31.02`) qabul qilinmaydi
- **⏰ Eslatma** — vaqtli vazifa uchun aniq vaqtda; xabarda **✅ Bajarildi** va
  **⏰ +15 daq / +1 soat / Ertaga** (kechiktirish) tugmalari
- **🔁 Takrorlanuvchi vazifalar** — kunlik va haftalik; bajarilganda keyingisi avtomatik yaratiladi
- **☀️ Bugungi reja** — har kuni ertalab o'zi keladi, istalgan payt tugma yoki `/today` bilan
- **Vazifalar ro'yxati** — bitta xabarda, bo'limlarga ajratilgan: ⚠️ Muddati o'tgan, 📅 Bugun,
  🗓 Keyingi, 📝 Muddatsiz. Bajarilganlar ro'yxatni egallamaydi — faqat soni ko'rsatiladi.
  10 tadan sahifalanadi (◀️ ▶️)
- **Vazifa kartasi** — ro'yxat ostida faqat raqamlar (5 tadan qatorda); raqam bosilsa o'sha xabarda
  karta ochiladi: ✅ Bajarildi, ⏰ Vaqtini o'zgartirish, ✏️ Nomini o'zgartirish,
  📅 Ertaga ko'chirish, 🗑 O'chirish,
  ◀️ Ro'yxatga qaytish.
  🧹 tugmasi bajarilganlarni bir bosishda tozalaydi
- **⚡ Bitta xabarda qo'shish** — `Hisobot ertaga 15:00`, `ertaga 15:00 Hisobot`,
  `Sport har kuni 07:00`: muddat matn boshidan yoki oxiridan ajratiladi va vazifa savolsiz
  saqlanadi; faqat kun yozilsa (`Kitob o'qish ertaga`) — bot faqat soatni so'raydi. Nom ichidagi
  raqamlar (`Python 3.12 o'rnatish`) muddat deb olinmaydi
- **📊 Statistika** — bugun va shu hafta bajarilganlar, 🔥 ketma-ket kunlar, jami, muddati o'tgan
- **📈 Haftalik hisobot** — har yakshanba 20:00 da: bajarilganlar, muddati o'tganlar,
  ketma-ketlik va keyingi 7 kunga reja. Sozlamalarda o'chirish mumkin
- **⚙️ Sozlamalar** (`/settings`) — shaxsiy ertalabki reja soati va haftalik hisobot
- **🛠 `/admin`** — bot egasi uchun (`ADMIN_ID`): foydalanuvchilar, faollar, vazifalar, eslatmalar
- `/start`, `/today`, `/help`, `/cancel` buyruqlari, Telegram menyusida ko'rinadi;
  noma'lum buyruq va matn bo'lmagan xabarga tushunarli javob beriladi
- Har bir foydalanuvchi faqat **o'z** vazifalarini ko'radi va o'zgartira oladi; bot faqat
  shaxsiy chatda ishlaydi (guruhda vazifalar aralashib ketmasligi uchun)

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
  reminders.py          eslatmalar, ertalabki reja va haftalik hisobot (fon vazifasi)
  progress.py           ketma-ketlik (streak) va haftalik hisobot matni (sof funksiyalar)
  clock.py              vaqt zonasidagi joriy vaqt (testda qotiriladi)
  keyboards.py          reply va inline tugmalar, CallbackData
  states.py             FSM holatlari
  handlers/
    start.py            /start, /help, /cancel, statistika
    tasks.py            vazifa qo'shish, ro'yxat, karta, callbacklar
    settings.py         ⚙️ shaxsiy sozlamalar
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
  tushishi bilan yuboriladi; qayta ishga tushirish takroriy xabar bermaydi. Xatolar ikkiga
  ajratiladi: doimiy (bot bloklangan, chat topilmadi) — eslatma belgilanadi va qayta
  urinilmaydi; vaqtinchalik (tarmoq) — belgilanmaydi va keyingi tekshiruvda qayta yuboriladi.
  Bitta foydalanuvchidagi xato navbatdagi boshqa eslatmalarni hech qachon to'xtatmaydi.
- **Eski tugmalar buzilmaydi.** Kechiktirish uchun yangi `SnoozeCallback` qo'shildi, mavjud
  `RemindCallback` o'zgartirilmadi — avval yuborilgan eslatmalardagi ✅ tugmasi ishlashda davom etadi.
- **Vaqt — dependency.** Joriy vaqt `Clock` obyekti orqali olinadi, shuning uchun testlarda
  "hozir"ni qotirib, eslatmalarni soatni kutmasdan tekshirish mumkin.
- **Migratsiya.** Eski bazada yangi ustunlar (`done_at`, `due_date`, `due_time`, `reminded`,
  `last_digest`, `repeat`, `digest_hour`, `weekly`, `last_weekly`) bo'lmasa, ishga tushishda avtomatik qo'shiladi. Ma'lumotlar yo'qolmaydi.

## Real ishlatishda topilgan va tuzatilgan xatolar

Bot haqiqiy aiogram `Dispatcher` orqali foydalanuvchi ssenariylari bilan sinab ko'rildi.
Topilgan har bir xato uchun avval yiqiladigan test yozildi, keyin tuzatildi:

| Xato | Oqibati | Tuzatish |
|---|---|---|
| Bitta chatga yuborib bo'lmasa (`chat not found`) eslatmalar sikli yiqilardi | Shu vazifadan keyingi **barcha foydalanuvchilarning** eslatmalari har 30 soniyada qayta tiqilib qolardi | Doimiy va vaqtinchalik xatolar ajratildi, har bir xabar alohida ishlanadi |
| Nom so'ralganda menyu tugmasi bosilsa | `📋 Vazifalarim` vazifa nomi bo'lib saqlanardi | Menyu tugmalari har qanday holatda menyu sifatida ishlaydi, nom sifatida rad etiladi |
| Oddiy matn yozilsa | Bot umuman javob bermasdi | Matn — tez qo'shish; noma'lum buyruq va stikerga yo'riqnoma |
| Kechqurun «Bugun» tanlansa | Vazifa «ertalabki rejaga» yozilardi, lekin bugungi reja o'tib ketgan — **eslatma hech qachon kelmasdi** | Kun tanlangandan keyin soat so'raladi; yetib bormaydigan variantlar ko'rsatilmaydi va rad etiladi |
| Bot guruhga qo'shilsa | Guruhda vazifa qo'shilib, eslatmalar shaxsiy chatga ketardi | Faqat shaxsiy chat xabarlari qayta ishlanadi |

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
| `ADMIN_ID` | yo'q | — | bot egasining Telegram ID'si, `/admin` uchun |

### Start'dan oldingi rasm

Tavsif matni avtomatik o'rnatiladi, lekin bo'sh chatdagi rasmni Telegram faqat @BotFather orqali
qabul qiladi: `/setdescriptionpic` → botni tanlang → `assets/welcome.png` ni yuboring.
Rasmni qayta yaratish: `make banner` (skript: `scripts/make_banner.py`).

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

108 ta test quyidagilarni qamraydi: bazaning CRUD amallari, muddat bo'yicha saralash va
sahifalash, boshqa foydalanuvchi vazifasiga kirishni taqiqlash, foreign key, eski sxemadan
migratsiya, muddat matnini o'qish (to'g'ri va noto'g'ri formatlar), vazifa qo'shish oqimi,
HTML escaping, ro'yxat va callbacklar, statistika, eslatmaning aniq vaqtda va faqat bir marta
kelishi, o'tib ketgan eslatma, ertalabki reja (kuniga bir marta, bo'sh bo'lsa yuborilmaydi),
botni bloklagan foydalanuvchi, `chat not found` va tarmoq xatosida navbat tiqilmasligi,
takrorlanuvchi vazifalar (o'tkazib yuborilgan kunlar bilan), kechiktirish, tozalash, tez
qo'shish, menyu tugmasining nom bo'lmasligi, admin huquqi.
