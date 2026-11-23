import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.clock import Clock
from bot.database import Database
from bot.handlers import tasks
from bot.keyboards import CANCEL, STATS, main_menu
from bot.texts import WELCOME_IMAGE, welcome_text

router = Router(name='start')
logger = logging.getLogger(__name__)

# Rasm Telegram'ga bir marta yuklanadi, keyin file_id orqali qayta yuboriladi (tez va trafiksiz)
_welcome_photo: dict[str, str] = {}

HELP_TEXT = (
    '<b>Buyruqlar</b>\n'
    '/start — bosh menyu\n'
    '/today — bugungi reja\n'
    '/help — yordam\n'
    '/cancel — amalni bekor qilish\n\n'
    '<b>Qanday ishlaydi</b>\n'
    "1. Vazifani shunchaki yozib yuboring (yoki «➕ Vazifa qo'shish») → muddatni tanlang\n"
    '2. <code>ertaga 15:00</code> kabi vaqt yozsangiz — aynan shu vaqtda ⏰ eslataman. '
    'Eslatmada ⏰ tugmalari bilan +15 daqiqa, +1 soat yoki ertagaga kechiktirish mumkin\n'
    '3. Faqat sana yozsangiz (<code>ertaga</code>, <code>25.11</code>) — '
    "o'sha kuni ertalab ☀️ rejada ko'rsataman\n"
    '4. <code>har kuni 09:00</code> yoki <code>har hafta</code> — 🔁 takrorlanuvchi vazifa: '
    'bajarilganda keyingisi avtomatik yaratiladi\n'
    "5. Ro'yxatda ✅ — bajarildi, 🗑 — o'chirish, 🧹 — bajarilganlarni tozalash"
)


async def send_welcome(message: Message, text: str) -> None:
    """Rasm + izoh; rasm bo'lmasa yoki yuborib bo'lmasa — oddiy matn (bot baribir javob beradi)."""
    photo = _welcome_photo.get('file_id')
    if photo is None and WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
    if photo is not None:
        try:
            sent = await message.answer_photo(photo, caption=text, reply_markup=main_menu)
        except TelegramBadRequest as error:
            logger.warning('Tanishtiruv rasmi yuborilmadi: %s', error.message)
            _welcome_photo.clear()
        else:
            file_id = sent.photo[-1].file_id if sent.photo else None
            if isinstance(file_id, str):
                _welcome_photo['file_id'] = file_id
            return
    await message.answer(text, reply_markup=main_menu)


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    user = message.from_user
    await db.add_user(user.id, user.full_name)
    await send_welcome(message, welcome_text(user.full_name))


@router.message(Command('help'))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command('cancel'))
@router.message(F.text == CANCEL)
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Bekor qilindi', reply_markup=main_menu)


@router.message(Command('today'))
async def today_command(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    await tasks.today_plan(message, state, db, clock)


@router.message(Command('admin'))
async def admin_handler(message: Message, db: Database, admin_id: int | None = None) -> None:
    """Bot egasi uchun umumiy statistika. Boshqalar uchun bu buyruq mavjud emasdek."""
    if admin_id is None or message.from_user.id != admin_id:
        await message.answer("Bunday buyruq yo'q. Buyruqlar ro'yxati: /help")
        return
    stats = await db.get_global_stats()
    await message.answer(
        '🛠 <b>Admin panel</b>\n\n'
        f'Foydalanuvchilar: {stats.users}\n'
        f'Faol (ochiq vazifasi bor): {stats.active_users}\n'
        f'Jami vazifalar: {stats.tasks}\n'
        f'Bajarilgan: {stats.done}\n'
        f'Kutilayotgan eslatmalar: {stats.pending_reminders}'
    )


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
