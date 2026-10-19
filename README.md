# RealProjectBot — Vazifalar boti

Telegram uchun shaxsiy vazifalar (todo) boti. aiogram 3, SQLite, FSM va inline tugmalar ishlatilgan.

## Imkoniyatlar

- `/start` — foydalanuvchini bazaga yozadi va menyu chiqaradi
- "➕ Vazifa qo'shish" — FSM orqali vazifa nomini so'raydi
- "📋 Vazifalarim" — har bir vazifa inline tugmalar bilan: ✅ Bajarildi, 🗑 O'chirish
- "📊 Statistika" — jami, bajarilgan va qolgan vazifalar soni
- `/cancel` — amalni bekor qilish
- Har bir foydalanuvchi faqat o'z vazifalarini ko'radi va o'zgartira oladi

## Tuzilishi

```
bot/
  config.py         .env sozlamalari
  database.py       SQLite bilan ishlash (Database klassi)
  loader.py         db obyekti
  states.py         FSM holatlari
  keyboards.py      reply va inline tugmalar, CallbackData
  handlers/
    start.py        /start, /help, /cancel, statistika
    tasks.py        vazifa qo'shish, ro'yxat, callbacklar
main.py
tests/
```

## Ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Baza `bot_data` volume ichida saqlanadi, konteyner o'chsa ham vazifalar yo'qolmaydi.

## Testlar

```bash
pytest
```
