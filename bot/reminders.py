"""Eslatmalar: vaqtli vazifa uchun aniq vaqtda xabar va ertalabki kunlik reja.

Har bir yuborish bazada belgilanadi (tasks.reminded, users.last_digest), shuning uchun bot qayta
ishga tushsa ham eslatma ikki marta kelmaydi va o'chiq turgan paytda o'tib ketganlari yo'qolmaydi —
ishga tushishi bilan yuboriladi.

Xatolar ikki xil:
- doimiy (botni bloklagan, chat topilmadi) — eslatma belgilanadi, qayta urinish foydasiz;
- vaqtinchalik (tarmoq, Telegram serveri) — belgilanmaydi, keyingi tekshiruvda qayta yuboriladi.
Ikkala holatda ham bitta foydalanuvchidagi xato navbatdagi boshqa eslatmalarni to'xtatmaydi.
"""

import asyncio
import logging
from datetime import date

from aiogram import Bot, html
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.clock import Clock
from bot.database import Database, Task
from bot.due import format_due
from bot.keyboards import done_keyboard, remind_keyboard
from bot.progress import WEEKLY_DAY, WEEKLY_HOUR, streak, week_start, weekly_text

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30  # soniya


def reminder_text(task: Task, today: date) -> str:
    due = format_due(task.due_date, task.due_time, today, task.repeat)
    return f'⏰ <b>Eslatma</b>\n{html.quote(task.title)}\n\nMuddat: {due}'


def left_text(minutes: int) -> str:
    if minutes < 60:
        return f'{max(minutes, 1)} daqiqa'
    if minutes < 1440:
        hours, rest = divmod(minutes, 60)
        return f'{hours} soat' + (f' {rest} daqiqa' if rest else '')
    return f'{round(minutes / 1440)} kun'


def pre_reminder_text(task: Task, minutes_left: int, today: date) -> str:
    due = format_due(task.due_date, task.due_time, today, task.repeat)
    return (
        f"🔔 <b>Eslatib qo'yaman</b>\n{html.quote(task.title)}\n\n"
        f'⏳ {left_text(minutes_left)} qoldi — {due}'
    )


def digest_text(tasks: list[Task], today: date) -> str:
    overdue = [t for t in tasks if t.due_date < today]
    today_tasks = [t for t in tasks if t.due_date == today]
    lines = ['☀️ <b>Bugungi reja</b>']
    if today_tasks:
        lines.append('')
        for task in today_tasks:
            at = f' — {task.due_time:%H:%M}' if task.due_time else ''
            star = '⭐ ' if task.important else ''
            lines.append(f'• {star}{html.quote(task.title)}{at}')
    if overdue:
        lines += ['', "⚠️ <b>Muddati o'tgan</b>"]
        for task in overdue:
            lines.append(f'• {html.quote(task.title)} — {format_due(task.due_date, None, today)}')
    return '\n'.join(lines)


async def _send(bot: Bot, user_id: int, text: str, **kwargs) -> bool:
    """True — yetkazildi yoki qayta urinish foydasiz; False — keyinroq qayta urinish kerak."""
    try:
        await bot.send_message(user_id, text, **kwargs)
    except TelegramForbiddenError:
        logger.info('Foydalanuvchi %s botni bloklagan, xabar tashlab ketildi', user_id)
    except TelegramBadRequest as error:
        logger.warning("Foydalanuvchi %s ga yuborib bo'lmadi: %s", user_id, error.message)
    except Exception:
        logger.exception('Foydalanuvchi %s ga yuborishda vaqtinchalik xato', user_id)
        return False
    return True


async def tick(bot: Bot, db: Database, clock: Clock, digest_hour: int) -> None:
    """Bitta tekshiruv: vaqti kelgan eslatmalar va (soat yetgan bo'lsa) ertalabki reja."""
    now = clock.now()
    today = now.date()

    # Oldindan ogohlantirish (sozlamalarda yoqilgan bo'lsa): «⏳ 1 soat qoldi»
    for task, minutes_left in await db.get_pre_reminders(now):
        text = pre_reminder_text(task, minutes_left, today)
        if await _send(bot, task.user_id, text, reply_markup=done_keyboard(task.id)):
            await db.mark_pre_reminded(task.id)

    for task in await db.get_due_reminders(now):
        text = reminder_text(task, today)
        if await _send(bot, task.user_id, text, reply_markup=remind_keyboard(task.id)):
            await db.mark_reminded(task.id)

    # Har bir foydalanuvchining o'z reja soati bo'lishi mumkin — filtr SQL'da
    for user_id in await db.get_digest_users(now, digest_hour):
        tasks = await db.get_digest_tasks(user_id, today)
        if await _send(bot, user_id, digest_text(tasks, today)):
            await db.set_digest_sent(user_id, today)

    if today.weekday() == WEEKLY_DAY and now.hour >= WEEKLY_HOUR:
        for user_id in await db.get_weekly_users(today):
            summary = await db.get_week_summary(user_id, week_start(today), today)
            days = streak(await db.get_done_days(user_id), today)
            if await _send(bot, user_id, weekly_text(summary, days, today)):
                await db.set_weekly_sent(user_id, today)


async def run_reminders(bot: Bot, db: Database, clock: Clock, digest_hour: int) -> None:
    logger.info('Eslatmalar xizmati ishga tushdi (reja soati %02d:00)', digest_hour)
    while True:
        try:
            await tick(bot, db, clock, digest_hour)
        except Exception:
            # Tarmoq yoki Telegram vaqtincha ishlamasa — belgilanmagan eslatma keyingi
            # aylanishda qayta yuboriladi, xizmatning o'zi esa to'xtamaydi
            logger.exception('Eslatmalar xizmatida xato')
        await asyncio.sleep(CHECK_INTERVAL)
