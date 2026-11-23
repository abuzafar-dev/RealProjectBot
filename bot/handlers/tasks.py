from datetime import date, datetime, timedelta

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.clock import Clock
from bot.database import Database, Task
from bot.due import REPEAT_LABEL, DueParseError, format_due, next_occurrence, parse_due
from bot.keyboards import (
    ADD_TASK,
    EVERY_DAY,
    MENU_BUTTONS,
    MY_TASKS,
    NO_DUE,
    TODAY_PLAN,
    ClearDoneCallback,
    PageCallback,
    RemindCallback,
    SnoozeCallback,
    TaskCallback,
    cancel_menu,
    due_menu,
    main_menu,
    task_card_keyboard,
    tasks_keyboard,
)
from bot.reminders import digest_text
from bot.states import AddTask

router = Router(name='tasks')

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
PAGE_SIZE = 10
EMPTY_TEXT = "Sizda hali vazifa yo'q. «➕ Vazifa qo'shish» tugmasini bosing yoki shunchaki yozing."
DUE_PROMPT = (
    '📅 Muddat qachon?\n'
    '<code>ertaga</code>, <code>25.11</code> — ertalabki rejaga tushadi\n'
    '<code>ertaga 15:00</code>, <code>18:30</code> — aynan shu vaqtda eslataman\n'
    '<code>har kuni 09:00</code>, <code>har hafta</code> — takrorlanadi 🔁'
)


SECTIONS = {
    'overdue': "⚠️ <b>Muddati o'tgan</b>",
    'today': '📅 <b>Bugun</b>',
    'later': '🗓 <b>Keyingi</b>',
    'none': '📝 <b>Muddatsiz</b>',
}


def section_of(task: Task, today: date) -> str:
    if task.due_date is None:
        return 'none'
    if task.due_date < today:
        return 'overdue'
    return 'today' if task.due_date == today else 'later'


def task_line(number: int, task: Task, today: date) -> str:
    """Bitta qator: raqam, nom va (bo'lim sarlavhasi aytmagan) qisqa muddat."""
    line = f'{number}. {html.quote(task.title)}'
    section = section_of(task, today)
    if section == 'today':
        when = f'{task.due_time:%H:%M}' if task.due_time else ''
    elif section == 'none':
        when = ''
    else:
        when = format_due(task.due_date, task.due_time, today)
    if when:
        line += f' · {when}'
    return line + (' 🔁' if task.repeat else '')


async def render_tasks(
    db: Database, user_id: int, page: int, today: date
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Ochiq vazifalar bo'limlarga ajratilgan holda; bajarilganlar faqat soni bilan."""
    stats = await db.get_stats(user_id)
    if stats.total == 0:
        return EMPTY_TEXT, None
    if stats.left == 0:
        text = f'🎉 <b>Hammasi bajarilgan!</b>\n\n✅ Bajarilgan: {stats.done} ta'
        return text, tasks_keyboard([], 0, 1, 1, done_count=stats.done)

    pages = (stats.left + PAGE_SIZE - 1) // PAGE_SIZE
    page = min(max(page, 0), pages - 1)
    offset = page * PAGE_SIZE
    tasks = await db.get_open_tasks(user_id, limit=PAGE_SIZE, offset=offset)

    lines = [f'📋 <b>Vazifalaringiz</b> · {stats.left} ta ochiq']
    current = None
    for number, task in enumerate(tasks, start=offset + 1):
        section = section_of(task, today)
        if section != current:
            lines += ['', SECTIONS[section]]
            current = section
        lines.append(task_line(number, task, today))
    if stats.done:
        lines += ['', f'✅ Bajarilgan: {stats.done} ta']
    lines += ['', '<i>Raqamni bosing — vazifa ochiladi 👇</i>']

    markup = tasks_keyboard(tasks, page, pages, offset + 1, done_count=stats.done)
    return '\n'.join(lines), markup


def task_card(task: Task, today: date) -> str:
    lines = [f'📝 <b>{html.quote(task.title)}</b>', '']
    if task.due_date is None:
        lines.append("Muddat: yo'q")
    elif task.due_date < today:
        days = (today - task.due_date).days
        due = format_due(task.due_date, task.due_time, today)
        lines.append(f"⚠️ Muddati o'tgan: {due} ({days} kun oldin)")
    else:
        lines.append(f'📅 Muddat: {format_due(task.due_date, task.due_time, today)}')
        if task.due_time:
            lines.append('⏰ Shu vaqtda eslataman')
    if task.repeat:
        lines.append(f'🔁 Takrorlanadi: {REPEAT_LABEL[task.repeat]}')
    return '\n'.join(lines)


async def refresh_list(callback: CallbackQuery, db: Database, clock: Clock, page: int) -> None:
    text, markup = await render_tasks(db, callback.from_user.id, page, clock.now().date())
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        # Matn o'zgarmagan bo'lsa Telegram xato qaytaradi — bu normal holat
        if 'message is not modified' not in str(error):
            raise


async def complete_task(db: Database, task: Task, now: datetime) -> Task | None:
    """Vazifani yopadi; takrorlanuvchi bo'lsa keyingisini yaratib, uni qaytaradi."""
    if not await db.mark_done(task.id, task.user_id) or not task.repeat:
        return None
    day = next_occurrence(task.due_date or now.date(), task.due_time, task.repeat, now)
    new_id = await db.add_task(task.user_id, task.title, day, task.due_time, task.repeat)
    return await db.get_task(new_id, task.user_id)


def next_text(task: Task | None, today: date) -> str:
    if task is None:
        return ''
    return f'\n🔁 Keyingisi: {format_due(task.due_date, task.due_time, today)}'


# --- menyu tugmalari: har qanday holatda ishlaydi va boshlangan amalni bekor qiladi ---


@router.message(F.text == ADD_TASK)
async def add_task_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddTask.title)
    await message.answer('Vazifa nomini yozing:', reply_markup=cancel_menu)


@router.message(F.text == MY_TASKS)
async def my_tasks(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    await state.clear()
    text, markup = await render_tasks(db, message.from_user.id, 0, clock.now().date())
    await message.answer(text, reply_markup=markup)


@router.message(F.text == TODAY_PLAN)
async def today_plan(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    await state.clear()
    today = clock.now().date()
    tasks = await db.get_digest_tasks(message.from_user.id, today)
    if not tasks:
        await message.answer(
            "☀️ Bugunga rejalashtirilgan vazifa yo'q. Dam oling yoki yangisini qo'shing 🙂",
            reply_markup=main_menu,
        )
        return
    await message.answer(digest_text(tasks, today), reply_markup=main_menu)


# --- vazifa qo'shish ---


async def accept_title(message: Message, state: FSMContext, raw: str) -> None:
    title = ' '.join(raw.split())
    if not title:
        await message.answer("Vazifa nomi bo'sh bo'lmasin. Qaytadan yozing:")
        return
    if len(title) < MIN_TITLE_LENGTH or not any(char.isalpha() for char in title):
        await message.answer(
            'Vazifa nomini tushunarli yozing (kamida 3 belgi, harflar bilan), '
            'masalan: <i>Hisobot topshirish</i>'
        )
        return
    if title in MENU_BUTTONS:
        await message.answer('Bu menyu tugmasi. Vazifa nomini matn qilib yozing:')
        return
    if len(title) > MAX_TITLE_LENGTH:
        await message.answer(
            f'Vazifa nomi {MAX_TITLE_LENGTH} belgidan oshmasin '
            f'(hozir {len(title)} ta). Qaytadan yozing:'
        )
        return
    await state.update_data(title=title)
    await state.set_state(AddTask.due)
    await message.answer(f'📝 {html.quote(title)}\n\n{DUE_PROMPT}', reply_markup=due_menu)


@router.message(AddTask.title, F.text)
async def add_task_title(message: Message, state: FSMContext) -> None:
    await accept_title(message, state, message.text)


@router.message(AddTask.due, F.text)
async def add_task_due(message: Message, state: FSMContext, db: Database, clock: Clock) -> None:
    now = clock.now()
    due_date = due_time = repeat = None
    if message.text != NO_DUE:
        text = 'har kuni' if message.text == EVERY_DAY else message.text
        try:
            due = parse_due(text, now)
        except DueParseError as error:
            await message.answer(str(error))
            return
        due_date, due_time, repeat = due.day, due.at, due.repeat

    title = (await state.get_data())['title']
    await db.add_user(message.from_user.id, message.from_user.full_name)
    await db.add_task(message.from_user.id, title, due_date, due_time, repeat)
    await state.clear()

    text = f"✅ Qo'shildi: {html.quote(title)}"
    if due_date:
        due_label = format_due(due_date, due_time, now.date(), repeat)
        if due_time:
            text += f'\n⏰ {due_label} — shu vaqtda eslataman'
        else:
            text += f'\n📅 Muddat: {due_label} (ertalabki rejada)'
    await message.answer(text, reply_markup=main_menu)


@router.message(AddTask.title)
@router.message(AddTask.due)
async def add_task_wrong(message: Message) -> None:
    await message.answer("Iltimos, matn ko'rinishida yozing")


# --- ro'yxatdagi tugmalar ---


async def open_task(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database
) -> Task | None:
    """Callback'dagi vazifani oladi; topilmasa yoki yopilgan bo'lsa — ogohlantiradi."""
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None or task.is_done:
        await callback.answer("Bu vazifa allaqachon bajarilgan yoki o'chirilgan", show_alert=True)
        return None
    return task


@router.callback_query(TaskCallback.filter(F.action == 'open'))
async def task_open(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    task = await open_task(callback, callback_data, db)
    if task is None:
        await refresh_list(callback, db, clock, callback_data.page)
        return
    await callback.message.edit_text(
        task_card(task, clock.now().date()),
        reply_markup=task_card_keyboard(task.id, callback_data.page),
    )
    await callback.answer()


@router.callback_query(TaskCallback.filter(F.action == 'done'))
async def task_done(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    task = await open_task(callback, callback_data, db)
    if task is None:
        await refresh_list(callback, db, clock, callback_data.page)
        return
    now = clock.now()
    following = await complete_task(db, task, now)
    await refresh_list(callback, db, clock, callback_data.page)
    await callback.answer(('✅ Bajarildi' + next_text(following, now.date())).strip())


@router.callback_query(TaskCallback.filter(F.action == 'tomorrow'))
async def task_tomorrow(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    task = await open_task(callback, callback_data, db)
    if task is None:
        await refresh_list(callback, db, clock, callback_data.page)
        return
    tomorrow = clock.now().date() + timedelta(days=1)
    await db.reschedule(task.id, task.user_id, tomorrow, task.due_time)
    await refresh_list(callback, db, clock, callback_data.page)
    await callback.answer("📅 Ertaga ko'chirildi")


@router.callback_query(TaskCallback.filter(F.action == 'delete'))
async def task_delete(
    callback: CallbackQuery, callback_data: TaskCallback, db: Database, clock: Clock
) -> None:
    deleted = await db.delete_task(callback_data.task_id, callback.from_user.id)
    await refresh_list(callback, db, clock, callback_data.page)
    if deleted:
        await callback.answer("🗑 O'chirildi")
    else:
        await callback.answer('Vazifa topilmadi', show_alert=True)


@router.callback_query(PageCallback.filter())
async def change_page(
    callback: CallbackQuery, callback_data: PageCallback, db: Database, clock: Clock
) -> None:
    await refresh_list(callback, db, clock, callback_data.page)
    await callback.answer()


@router.callback_query(ClearDoneCallback.filter())
async def clear_done(callback: CallbackQuery, db: Database, clock: Clock) -> None:
    removed = await db.clear_done(callback.from_user.id)
    await refresh_list(callback, db, clock, 0)
    await callback.answer(f'🧹 {removed} ta bajarilgan vazifa tozalandi')


# --- eslatma xabaridagi tugmalar ---


@router.callback_query(RemindCallback.filter())
async def remind_done(
    callback: CallbackQuery, callback_data: RemindCallback, db: Database, clock: Clock
) -> None:
    """Eslatma xabaridagi ✅ — vazifani yopadi va xabarni o'zgartiradi."""
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None:
        await callback.answer('Vazifa topilmadi', show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return
    now = clock.now()
    following = await complete_task(db, task, now)
    await callback.message.edit_text(
        f'✅ Bajarildi: <s>{html.quote(task.title)}</s>' + next_text(following, now.date())
    )
    await callback.answer('Barakalla! 👏')


@router.callback_query(SnoozeCallback.filter())
async def snooze(
    callback: CallbackQuery, callback_data: SnoozeCallback, db: Database, clock: Clock
) -> None:
    """⏰ Kechiktirish: +15 daqiqa, +1 soat yoki ertaga shu vaqtda qayta eslatadi."""
    task = await db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None or task.is_done:
        await callback.answer('Vazifa topilmadi yoki allaqachon bajarilgan', show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return
    now = clock.now()
    if callback_data.minutes:
        when = now + timedelta(minutes=callback_data.minutes)
    else:
        at = task.due_time or now.time()
        when = datetime.combine(now.date() + timedelta(days=1), at)
    await db.reschedule(task.id, task.user_id, when.date(), when.time())
    label = format_due(when.date(), when.time(), now.date())
    await callback.message.edit_text(
        f'⏰ <b>Kechiktirildi</b>\n{html.quote(task.title)}\n\n{label} da qayta eslataman'
    )
    await callback.answer(f'{label} da eslataman')


# --- boshqa hech qaysi handlerga tushmagan xabarlar (eng oxirida) ---


@router.message(StateFilter(None), F.text.startswith('/'))
async def unknown_command(message: Message) -> None:
    await message.answer("Bunday buyruq yo'q. Buyruqlar ro'yxati: /help", reply_markup=main_menu)


@router.message(StateFilter(None), F.text)
async def quick_add(message: Message, state: FSMContext) -> None:
    """Menyusiz tez qo'shish: oddiy yozilgan matn — yangi vazifa nomi."""
    await accept_title(message, state, message.text)


@router.message(StateFilter(None))
async def non_text(message: Message) -> None:
    await message.answer(
        "Men faqat matnni tushunaman. Vazifa qo'shish uchun uni yozib yuboring ✍️",
        reply_markup=main_menu,
    )
