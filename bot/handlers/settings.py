"""⚙️ Sozlamalar: shaxsiy ertalabki reja soati va haftalik hisobot."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database
from bot.keyboards import DIGEST_HOURS, LEAD_OPTIONS, SETTINGS, SettingsCallback, settings_keyboard
from bot.progress import WEEKLY_HOUR
from bot.reminders import left_text

LEAD_MINUTES = {minutes for _, minutes in LEAD_OPTIONS}

router = Router(name='settings')

DEFAULT_DIGEST_HOUR = 8


async def render_settings(db: Database, user_id: int, default_hour: int):
    settings = await db.get_settings(user_id)
    hour = settings.digest_hour or default_hour
    weekly = f'har yakshanba {WEEKLY_HOUR}:00 da keladi' if settings.weekly else "o'chirilgan"
    lead = f'{left_text(settings.lead_minutes)} oldin' if settings.lead_minutes else "o'chiq"
    text = (
        '⚙️ <b>Sozlamalar</b>\n\n'
        f'☀️ Ertalabki reja: <b>{hour:02d}:00</b>\n'
        "Shu soatda bugungi va muddati o'tgan vazifalar ro'yxati keladi.\n\n"
        f'🔔 Oldindan ogohlantirish: {lead}\n'
        'Vaqtli vazifadan shuncha oldin «⏳ qoldi» xabari keladi.\n\n'
        f'📈 Haftalik hisobot: {weekly}\n'
        'Bajarilganlar, ketma-ketlik va keyingi haftaga reja.\n\n'
        "<i>Reja soatini tanlang yoki hisobotni yoqing/o'chiring 👇</i>"
    )
    return text, settings_keyboard(hour, settings.weekly, settings.lead_minutes)


@router.message(Command('settings'))
@router.message(F.text == SETTINGS)
async def settings_handler(
    message: Message,
    state: FSMContext,
    db: Database,
    digest_hour: int = DEFAULT_DIGEST_HOUR,
) -> None:
    await state.clear()
    await db.add_user(message.from_user.id, message.from_user.full_name)
    text, markup = await render_settings(db, message.from_user.id, digest_hour)
    await message.answer(text, reply_markup=markup)


@router.callback_query(SettingsCallback.filter())
async def settings_change(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    db: Database,
    digest_hour: int = DEFAULT_DIGEST_HOUR,
) -> None:
    user_id = callback.from_user.id
    await db.add_user(user_id, callback.from_user.full_name)
    if callback_data.action == 'hour' and callback_data.value in DIGEST_HOURS:
        await db.set_digest_hour(user_id, callback_data.value)
        notice = f'☀️ Reja endi {callback_data.value:02d}:00 da keladi'
    elif callback_data.action == 'weekly':
        enabled = await db.toggle_weekly(user_id)
        notice = '📈 Haftalik hisobot yoqildi' if enabled else "📈 Haftalik hisobot o'chirildi"
    elif callback_data.action == 'lead' and callback_data.value in LEAD_MINUTES:
        minutes = callback_data.value or None
        await db.set_lead_minutes(user_id, minutes)
        notice = (
            f'🔔 {left_text(minutes)} oldin ogohlantiraman'
            if minutes
            else "🔔 Oldindan ogohlantirish o'chirildi"
        )
    else:
        await callback.answer()
        return
    text, markup = await render_settings(db, user_id, digest_hour)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if 'message is not modified' not in str(error):
            raise
    await callback.answer(notice)
