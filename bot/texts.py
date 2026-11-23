"""Botning foydalanuvchiga ko'rinadigan tanishtiruv matnlari va rasmi."""

from pathlib import Path

from aiogram import html

WELCOME_IMAGE = Path(__file__).resolve().parent.parent / 'assets' / 'welcome.png'

# Start bosilishidan oldin bo'sh chatda ko'rinadi («Bu bot nima qila oladi?»), 512 belgigacha
DESCRIPTION = (
    "⏰ Vazifalaringizni yozib qo'ying — vaqti kelganda o'zim eslataman.\n"
    'Bitta xabar kifoya: «Hisobot ertaga 15:00»\n'
    '\n'
    'Nima qila olaman:\n'
    '• ⏰ Aniq vaqtda eslatma (+15 daq / +1 soat / ertaga kechiktirish)\n'
    '• ☀️ Har kuni ertalab bugungi reja\n'
    '• 🔁 Har kuni / har hafta / har oy takrorlanuvchi vazifalar\n'
    "• 📋 Ro'yxat: ✅ bajarildi, 🗑 o'chirish\n"
    '• 📊 Statistika, 🔥 ketma-ketlik va 📈 haftalik hisobot\n'
    '\n'
    'Boshlash uchun START ni bosing 👇'
)

# Bot profilida va ulashilganda ko'rinadi, 120 belgigacha
SHORT_DESCRIPTION = (
    "Vazifalarni yozing — vaqti kelganda o'zim eslataman ⏰ Kunlik reja, takrorlanish, statistika"
)


def welcome_text(full_name: str) -> str:
    """/start javobi — rasm ostidagi izoh.

    Imkoniyatlar ro'yxati tavsifda, ishlash tartibi rasmda bor — bu yerda takrorlanmaydi,
    faqat salom va bitta aniq keyingi qadam.
    """
    return (
        f'Assalomu alaykum, <b>{html.quote(full_name)}</b>! 👋\n'
        '\n'
        'Birinchi vazifangizni hoziroq yozib yuboring, masalan: <i>Hisobot topshirish</i>\n'
        '\n'
        'Barcha imkoniyatlar: /help'
    )
