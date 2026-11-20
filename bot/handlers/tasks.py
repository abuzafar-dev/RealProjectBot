from datetime import date

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.clock import Clock
from bot.database import Database, Task
from bot.due import DueParseError, format_due, parse_due
from bot.keyboards import (
    ADD_TASK,
    MY_TASKS,
    NO_DUE,
    PageCallback,
    RemindCallback,
    TaskCallback,
    cancel_menu,
    due_menu,
    main_menu,
    tasks_keyboard,
)
from bot.states import AddTask

router = Router(name='tasks')

MAX_TITLE_LENGTH = 200
PAGE_SIZE = 10
EMPTY_TEXT = "Sizda hali vazifa yo'q. «➕ Vazifa qo'shish» tugmasini bosing."


def task_line(number: int, task: Task, today: date) -> str:
    title = html.quote(task.title)
    if task.is_done:
        return f'{number}. ✅ <s>{title}</s>'
    if task.due_date is None:
        return f'{number}. 🕐 {title}'
    due = format_due(task.due_date, task.due_time, today)
    mark = '⚠️' if task.due_date < today else '📅'
    return f'{number}. 🕐 {title} — {mark} {due}'


async def render_tasks(
    db: Database, user_id: int, page: int, today: date
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Vazifalar ro'yxatining bitta sahifasini matn va tugmalar ko'rinishida qaytaradi."""
    stats = await db.get_stats(user_id)
    if stats.total == 0:
        return EMPTY_TEXT, None

    pages = (stats.total + PAGE_SIZE - 1) // PAGE_SIZE
    page = min(max(page, 0), pages - 1)
    offset = page * PAGE_SIZE
    tasks = await db.get_tasks(user_id, limit=PAGE_SIZE, offset=offset)

    lines = [f'📋 <b>Vazifalaringiz</b> ({stats.done}/{stats.total} bajarilgan)', '']
    for number, task in enumerate(tasks, start=offset + 1):
        lines.append(task_line(number, task, today))

    return '\n'.join(lines), tasks_keyboard(tasks, page, pages, start_number=offset + 1)


async def refresh_list(callback: CallbackQuery, db: Database, clock: Clock, page: int) -> None:
    text, markup = await render_tasks(db, callback.from_user.id, page, clock.now().date())
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        # Matn o'zgarmagan bo'lsa Telegram xato qaytaradi — bu normal holat
        if 'message is not modified' not in str(error):
            raise


@router.message(F.text == ADD_TASK)
async def add_task_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddTask.title)
    await message.answer('Vazifa nomini yozing:', reply_markup=cancel_menu)


@router.message(AddTask.title, F.text)
async def add_task_title(message: Message, state: FSMContext) -> None:
    title = ' '.join(message.text.split())
    if not title:
        await message.answer("Vazifa nomi bo'sh bo'lmasin. Qaytadan yozing:")
        return
    if len(title) > MAX_TITLE_LENGTH:
        await message.answer(
            f'Vazifa nomi {MAX_TITLE_LENGTH} belgidan oshmasin '
            f'(hozir {len(title)} ta). Qaytadan yozing:'
        )
        return
    await state.update_data(title=title)
    await state.set_state(AddTask.due)
    await message.answer(
        '📅 Muddat qachon?\n'
        '<code>ertaga</code>, <code>25.11</code> — ertalabki rejaga tushadi\n'
        '<code>ertaga 15:00</code>, <code>18:30</code> — aynan shu vaqtda eslataman',
        reply_markup=due_menu,
    )


@router.message(AddTask.due, F.text)
async def add_task_due(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    now = clock.now()
    due_date = due_time = None
    if message.text != NO_DUE:
        try:
            due = parse_due(message.text, now)
        except DueParseError as error:
            await message.answer(str(error))
            return
        due_date, due_time = due.day, due.at

    title = (await state.get_data())['title']
    await db.add_user(message.from_user.id, message.from_user.full_name)
    await db.add_task(message.from_user.id, title, due_date, due_time)
    await state.clear()

    text = f"✅ Qo'shildi: {html.quote(title)}"
    if due_time:
        text += f'\n⏰ {format_due(due_date, due_time, now.date())} da eslataman'
    elif due_date:
        text += f'\n📅 Muddat: {format_due(due_date, None, now.date())} (ertalabki rejada)'
    await message.answer(text, reply_markup=main_menu)


@router.message(AddTask.title)
@router.message(AddTask.due)
async def add_task_wrong(message: Message) -> None:
    await message.answer("Iltimos, matn ko'rinishida yozing")


@router.message(F.text == MY_TASKS)
async def my_tasks(message: Message, db: Database, clock: Clock) -> None:
    text, markup = await render_tasks(db, message.from_user.id, 0, clock.now().date())
    await message.answer(text, reply_markup=markup)


@router.callback_query(TaskCallback.filter(F.action == 'done'))
async def task_done(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None:
        await callback.answer('Vazifa topilmadi', show_alert=True)
        await refresh_list(callback, db, clock, callback_data.page)
        return
    await db.mark_done(task.id, callback.from_user.id)
    await refresh_list(callback, db, clock, callback_data.page)
    await callback.answer('Bajarildi deb belgilandi')


@router.callback_query(TaskCallback.filter(F.action == 'delete'))
async def task_delete(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    deleted = await db.delete_task(callback_data.task_id, callback.from_user.id)
    await refresh_list(callback, db, clock, callback_data.page)
    if deleted:
        await callback.answer("O'chirildi")
    else:
        await callback.answer('Vazifa topilmadi', show_alert=True)


@router.callback_query(PageCallback.filter())
async def change_page(
    callback: CallbackQuery, callback_data: PageCallback, db: Database, clock: Clock
) -> None:
    await refresh_list(callback, db, clock, callback_data.page)
    await callback.answer()


@router.callback_query(RemindCallback.filter())
async def remind_done(callback: CallbackQuery, callback_data: RemindCallback, db: Database) -> None:
    """Eslatma xabaridagi ✅ — vazifani yopadi va xabarni o'zgartiradi."""
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None:
        await callback.answer('Vazifa topilmadi', show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return
    await db.mark_done(task.id, callback.from_user.id)
    await callback.message.edit_text(f'✅ Bajarildi: <s>{html.quote(task.title)}</s>')
    await callback.answer('Barakalla! 👏')
