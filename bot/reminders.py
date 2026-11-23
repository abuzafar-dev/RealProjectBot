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
from bot.keyboards import remind_keyboard

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30  # soniya


def reminder_text(task: Task, today: date) -> str:
    due = format_due(task.due_date, task.due_time, today, task.repeat)
    return f'⏰ <b>Eslatma</b>\n{html.quote(task.title)}\n\nMuddat: {due}'


def digest_text(tasks: list[Task], today: date) -> str:
    overdue = [t for t in tasks if t.due_date < today]
    today_tasks = [t for t in tasks if t.due_date == today]
    lines = ['☀️ <b>Bugungi reja</b>']
    if today_tasks:
        lines.append('')
        for task in today_tasks:
            at = f' — {task.due_time:%H:%M}' if task.due_time else ''
            lines.append(f'• {html.quote(task.title)}{at}')
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

    for task in await db.get_due_reminders(now):
        text = reminder_text(task, today)
        if await _send(bot, task.user_id, text, reply_markup=remind_keyboard(task.id)):
            await db.mark_reminded(task.id)

    if now.hour >= digest_hour:
        for user_id in await db.get_digest_users(today):
            tasks = await db.get_digest_tasks(user_id, today)
            if await _send(bot, user_id, digest_text(tasks, today)):
                await db.set_digest_sent(user_id, today)


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
