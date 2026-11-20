from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import Database
from bot.keyboards import CANCEL, STATS, main_menu

router = Router(name='start')

HELP_TEXT = (
    '<b>Buyruqlar</b>\n'
    '/start — bosh menyu\n'
    '/help — yordam\n'
    '/cancel — amalni bekor qilish\n\n'
    "Vazifa qo'shing, ro'yxatda ✅ bilan bajarilganini belgilang yoki 🗑 bilan o'chiring."
)


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = message.from_user
    await db.add_user(user.id, user.full_name)
    await message.answer(
        f'Assalomu alaykum, <b>{html.quote(user.full_name)}</b>!\n'
        'Men vazifalaringizni eslab qoluvchi botman. Quyidagi menyudan foydalaning.',
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
async def stats_handler(message: Message, db: Database) -> None:
    stats = await db.get_stats(message.from_user.id)
    filled = stats.percent // 10
    bar = '▰' * filled + '▱' * (10 - filled)
    await message.answer(
        '📊 <b>Statistika</b>\n\n'
        f'Jami vazifalar: {stats.total}\n'
        f'Bajarilgan: {stats.done}\n'
        f'Qolgan: {stats.left}\n\n'
        f'{bar} {stats.percent}%'
    )
