from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.database import Database
from bot.keyboards import (
    ADD_TASK,
    MY_TASKS,
    PageCallback,
    TaskCallback,
    cancel_menu,
    main_menu,
    tasks_keyboard,
)
from bot.states import AddTask

router = Router(name='tasks')

MAX_TITLE_LENGTH = 200
PAGE_SIZE = 10
EMPTY_TEXT = "Sizda hali vazifa yo'q. «➕ Vazifa qo'shish» tugmasini bosing."


async def render_tasks(
    db: Database, user_id: int, page: int
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
        title = html.quote(task.title)
        if task.is_done:
            lines.append(f'{number}. ✅ <s>{title}</s>')
        else:
            lines.append(f'{number}. 🕐 {title}')

    return '\n'.join(lines), tasks_keyboard(tasks, page, pages, start_number=offset + 1)


async def refresh_list(callback: CallbackQuery, db: Database, page: int) -> None:
    text, markup = await render_tasks(db, callback.from_user.id, page)
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
async def add_task_title(message: Message, state: FSMContext, db: Database) -> None:
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
    await db.add_user(message.from_user.id, message.from_user.full_name)
    await db.add_task(message.from_user.id, title)
    await state.clear()
    await message.answer(f"✅ Qo'shildi: {html.quote(title)}", reply_markup=main_menu)


@router.message(AddTask.title)
async def add_task_wrong(message: Message) -> None:
    await message.answer("Iltimos, vazifa nomini matn ko'rinishida yozing")


@router.message(F.text == MY_TASKS)
async def my_tasks(message: Message, db: Database) -> None:
    text, markup = await render_tasks(db, message.from_user.id, page=0)
    await message.answer(text, reply_markup=markup)


@router.callback_query(TaskCallback.filter(F.action == 'done'))
async def task_done(callback: CallbackQuery, callback_data: TaskCallback, db: Database) -> None:
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None:
        await callback.answer('Vazifa topilmadi', show_alert=True)
        await refresh_list(callback, db, callback_data.page)
        return
    await db.mark_done(task.id, callback.from_user.id)
    await refresh_list(callback, db, callback_data.page)
    await callback.answer('Bajarildi deb belgilandi')


@router.callback_query(TaskCallback.filter(F.action == 'delete'))
async def task_delete(callback: CallbackQuery, callback_data: TaskCallback, db: Database) -> None:
    deleted = await db.delete_task(callback_data.task_id, callback.from_user.id)
    await refresh_list(callback, db, callback_data.page)
    if deleted:
        await callback.answer("O'chirildi")
    else:
        await callback.answer('Vazifa topilmadi', show_alert=True)


@router.callback_query(PageCallback.filter())
async def change_page(callback: CallbackQuery, callback_data: PageCallback, db: Database) -> None:
    await refresh_list(callback, db, callback_data.page)
    await callback.answer()
