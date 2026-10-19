from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import CANCEL, STATS, main_menu
from bot.loader import db

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.add_user(user.id, user.full_name)
    await message.answer(
        f"Assalomu alaykum, <b>{html.quote(user.full_name)}</b>!\n"
        "Men vazifalaringizni eslab qoluvchi botman. Quyidagi menyudan foydalaning.",
        reply_markup=main_menu,
    )


@router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        "/start - bosh menyu\n"
        "/help - yordam\n"
        "/cancel - amalni bekor qilish\n\n"
        "Vazifa qo'shing, bajarilganini belgilang yoki o'chiring."
    )


@router.message(Command('cancel'))
@router.message(F.text == CANCEL)
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Bekor qilindi', reply_markup=main_menu)


@router.message(F.text == STATS)
async def stats_handler(message: Message):
    total, done = db.get_stats(message.from_user.id)
    await message.answer(
        f"📊 Statistika\n\n"
        f"Jami vazifalar: {total}\n"
        f"Bajarilgan: {done}\n"
        f"Qolgan: {total - done}"
    )
