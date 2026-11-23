"""🔍 /find — vazifani nomidan qidirish, 📤 /export — barcha vazifalarni CSV qilib yuborish."""

import csv
import io

from aiogram import Router, html
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.clock import Clock
from bot.database import Database, Task
from bot.due import format_due, repeat_label
from bot.keyboards import TaskCallback, main_menu

router = Router(name='tools')

SEARCH_LIMIT = 10
MIN_QUERY = 2


def search_line(number: int, task: Task, today) -> str:
    title = html.quote(task.title)
    if task.is_done:
        return f'{number}. ✅ <s>{title}</s>'
    star = '⭐ ' if task.important else ''
    due = f' · {format_due(task.due_date, task.due_time, today)}' if task.due_date else ''
    return f'{number}. {star}{title}{due}'


@router.message(Command('find'))
async def find_handler(
    message: Message, command: CommandObject, state: FSMContext, db: Database, clock: Clock
) -> None:
    await state.clear()
    query = ' '.join((command.args or '').split())
    if len(query) < MIN_QUERY:
        await message.answer(
            "🔍 Qidirish uchun so'z yozing, masalan: <code>/find hisobot</code>",
            reply_markup=main_menu,
        )
        return
    found = await db.search_tasks(message.from_user.id, query, SEARCH_LIMIT)
    if not found:
        await message.answer(
            f"🔍 «{html.quote(query)}» bo'yicha vazifa topilmadi", reply_markup=main_menu
        )
        return

    today = clock.now().date()
    lines = [f'🔍 <b>«{html.quote(query)}»</b> — {len(found)} ta', '']
    lines += [search_line(i, task, today) for i, task in enumerate(found, start=1)]
    builder = InlineKeyboardBuilder()
    numbers = 0
    for i, task in enumerate(found, start=1):
        if not task.is_done:  # bajarilganning kartasi yo'q — faqat ochiqlari ochiladi
            builder.button(text=str(i), callback_data=TaskCallback(action='open', task_id=task.id))
            numbers += 1
    builder.adjust(5)
    if numbers:
        lines += ['', '<i>Raqamni bosing — vazifa ochiladi 👇</i>']
    await message.answer('\n'.join(lines), reply_markup=builder.as_markup() if numbers else None)


def tasks_csv(tasks: list[Task]) -> bytes:
    """Excel o'zbekcha harflarni to'g'ri ochishi uchun UTF-8 BOM bilan."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ['Vazifa', 'Holat', 'Sana', 'Vaqt', 'Takrorlanish', 'Muhim', "Qo'shilgan", 'Bajarilgan']
    )
    for task in tasks:
        writer.writerow(
            [
                task.title,
                'bajarilgan' if task.is_done else 'ochiq',
                task.due_date.strftime('%d.%m.%Y') if task.due_date else '',
                task.due_time.strftime('%H:%M') if task.due_time else '',
                repeat_label(task.repeat, task.due_date) if task.repeat else '',
                'ha' if task.important else '',
                task.created_at or '',
                task.done_at or '',
            ]
        )
    return buffer.getvalue().encode('utf-8-sig')


@router.message(Command('export'))
async def export_handler(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    await state.clear()
    tasks = await db.get_tasks(message.from_user.id)
    if not tasks:
        await message.answer("Eksport qilish uchun hali vazifa yo'q", reply_markup=main_menu)
        return
    name = f'vazifalar_{clock.now():%Y-%m-%d}.csv'
    await message.answer_document(
        BufferedInputFile(tasks_csv(tasks), filename=name),
        caption=f"📤 {len(tasks)} ta vazifa. Excel yoki Google Sheets'da ochiladi",
        reply_markup=main_menu,
    )
