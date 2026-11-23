"""Botning foydalanuvchiga ko'rinadigan tanishtiruv matnlari va rasmi."""

from pathlib import Path

from aiogram import html

WELCOME_IMAGE = Path(__file__).resolve().parent.parent / 'assets' / 'welcome.png'

# Start bosilishidan oldin bo'sh chatda ko'rinadi («Bu bot nima qila oladi?»), 512 belgigacha
DESCRIPTION = (
    "⏰ Vazifalaringizni yozib qo'ying — vaqti kelganda o'zim eslataman.\n"
    '\n'
    'Nima qila olaman:\n'
    '• ⏰ Aniq vaqtda eslatma (+15 daq / +1 soat / ertaga kechiktirish)\n'
    '• ☀️ Har kuni ertalab bugungi reja\n'
    '• 🔁 Har kuni / har hafta takrorlanuvchi vazifalar\n'
    "• 📋 Ro'yxat: ✅ bajarildi, 🗑 o'chirish\n"
    '• 📊 Statistika va progress\n'
    '\n'
    'Boshlash uchun START ni bosing 👇'
)

# Bot profilida va ulashilganda ko'rinadi, 120 belgigacha
SHORT_DESCRIPTION = (
    "Vazifalarni yozing — vaqti kelganda o'zim eslataman ⏰ Kunlik reja, takrorlanish, statistika"
)


def welcome_text(full_name: str) -> str:
    """/start javobi — rasm ostidagi izoh (1024 belgigacha)."""
    return (
        f'Assalomu alaykum, <b>{html.quote(full_name)}</b>! 👋\n'
        "Men — <b>eslatuvchi vazifalar boti</b>. Ishlaringizni yozib qo'ysangiz, "
        "vaqti kelganda o'zim eslataman — ilovani ochishni unutsangiz ham.\n"
        '\n'
        '<b>Boshlash — 10 soniya:</b>\n'
        '1. Vazifani shunchaki yozing: <i>Hisobot topshirish</i>\n'
        '2. Muddatini yozing: <code>ertaga 15:00</code>\n'
        '3. Tamom — ertaga 15:00 da ⏰ eslataman\n'
        '\n'
        '<b>Yana:</b> 🔁 <code>har kuni 09:00</code> · ☀️ ertalabki reja · 📊 statistika\n'
        'Batafsil: /help'
    )
