from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.clock import Clock
from bot.database import Database
from bot.keyboards import CANCEL, STATS, main_menu

router = Router(name='start')

HELP_TEXT = (
    '<b>Buyruqlar</b>\n'
    '/start — bosh menyu\n'
    '/help — yordam\n'
    '/cancel — amalni bekor qilish\n\n'
    '<b>Qanday ishlaydi</b>\n'
    "1. «➕ Vazifa qo'shish» → nomini yozing → muddatni tanlang\n"
    '2. <code>ertaga 15:00</code> kabi vaqt yozsangiz — aynan shu vaqtda ⏰ eslataman\n'
    '3. Faqat sana yozsangiz (<code>ertaga</code>, <code>25.11</code>) — '
    "o'sha kuni ertalab ☀️ rejada ko'rsataman\n"
    "4. Ro'yxatda ✅ — bajarildi, 🗑 — o'chirish"
)


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = message.from_user
    await db.add_user(user.id, user.full_name)
    await message.answer(
        f'Assalomu alaykum, <b>{html.quote(user.full_name)}</b>!\n'
        "Men vazifalaringizni eslab qolaman va vaqti kelganda o'zim eslataman — "
        'ilovani ochishni unutsangiz ham.\n'
        'Batafsil: /help',
        reply_markup=main_menu,
    )


@router.message(Command('help'))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command('cancel'))
@router.message(F.text == CANCEL)
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Bekor qilindi', reply_markup=main_menu)


@router.message(F.text == STATS)
async def stats_handler(message: Message, db: Database, clock: Clock) -> None:
    stats = await db.get_stats(message.from_user.id)
    overdue = await db.count_overdue(message.from_user.id, clock.now().date())
    filled = stats.percent // 10
    bar = '▰' * filled + '▱' * (10 - filled)
    await message.answer(
        '📊 <b>Statistika</b>\n\n'
        f'Jami vazifalar: {stats.total}\n'
        f'Bajarilgan: {stats.done}\n'
        f'Qolgan: {stats.left}\n'
        f"Muddati o'tgan: {overdue}\n\n"
        f'{bar} {stats.percent}%'
    )
