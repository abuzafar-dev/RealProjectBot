from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import Task

ADD_TASK = "➕ Vazifa qo'shish"
MY_TASKS = '📋 Vazifalarim'
STATS = '📊 Statistika'
TODAY_PLAN = '☀️ Bugungi reja'
SETTINGS = '⚙️ Sozlamalar'
CANCEL = '❌ Bekor qilish'
TODAY = 'Bugun'
TOMORROW = 'Ertaga'
NO_DUE = '⏭ Muddatsiz'
EVERY_DAY = '🔁 Har kuni'
MORNING = '☀️ Ertalabki rejada'

# Menyu tugmalari — vazifa nomi sifatida qabul qilinmaydi
MENU_BUTTONS = {ADD_TASK, MY_TASKS, STATS, TODAY_PLAN, SETTINGS, CANCEL}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_TASK)],
        [KeyboardButton(text=MY_TASKS), KeyboardButton(text=TODAY_PLAN)],
        [KeyboardButton(text=STATS), KeyboardButton(text=SETTINGS)],
    ],
    resize_keyboard=True,
)

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL)]],
    resize_keyboard=True,
)


day_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=TODAY), KeyboardButton(text=TOMORROW)],
        [KeyboardButton(text=EVERY_DAY), KeyboardButton(text=NO_DUE)],
        [KeyboardButton(text=CANCEL)],
    ],
    resize_keyboard=True,
)


class TaskCallback(CallbackData, prefix='task'):
    action: str  # 'open' | 'done' | 'star' | 'edit' | 'rename' | 'tomorrow' | 'delete'
    task_id: int
    page: int = 0


class PageCallback(CallbackData, prefix='page'):
    page: int


class RemindCallback(CallbackData, prefix='remind'):
    task_id: int


class SnoozeCallback(CallbackData, prefix='snooze'):
    task_id: int
    minutes: int  # 0 — ertaga shu vaqtda


class ClearDoneCallback(CallbackData, prefix='clear'):
    pass


class SettingsCallback(CallbackData, prefix='set'):
    action: str  # 'hour' | 'weekly' | 'lead'
    value: int = 0


DIGEST_HOURS = [6, 7, 8, 9, 10]
# (tugma matni, daqiqa); 0 — o'chiq
LEAD_OPTIONS = [("O'chiq", 0), ('15 daq', 15), ('1 soat', 60), ('1 kun', 1440)]


def settings_keyboard(
    digest_hour: int, weekly: bool, lead: int | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hour in DIGEST_HOURS:
        mark = '✓ ' if hour == digest_hour else ''
        builder.button(
            text=f'{mark}{hour:02d}:00', callback_data=SettingsCallback(action='hour', value=hour)
        )
    weekly_text = '✅ yoqilgan' if weekly else "❌ o'chiq"
    weekly_text = f'📈 Haftalik hisobot: {weekly_text}'
    for text, minutes in LEAD_OPTIONS:
        mark = '✓ ' if minutes == (lead or 0) else ''
        builder.button(
            text=f'🔔 {mark}{text}', callback_data=SettingsCallback(action='lead', value=minutes)
        )
    builder.button(text=weekly_text, callback_data=SettingsCallback(action='weekly'))
    builder.adjust(len(DIGEST_HOURS), len(LEAD_OPTIONS), 1)
    return builder.as_markup()


SNOOZE_OPTIONS = [('+15 daq', 15), ('+1 soat', 60), ('Ertaga', 0)]


def done_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Bajarildi', callback_data=RemindCallback(task_id=task_id))
    return builder.as_markup()


def remind_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Bajarildi', callback_data=RemindCallback(task_id=task_id))
    for text, minutes in SNOOZE_OPTIONS:
        builder.button(
            text=f'⏰ {text}', callback_data=SnoozeCallback(task_id=task_id, minutes=minutes)
        )
    builder.adjust(1, 3)
    return builder.as_markup()


NUMBERS_PER_ROW = 5


def time_menu(options: list[str], with_morning: bool) -> ReplyKeyboardMarkup:
    """«Soat nechada?» qadami: nisbiy vaqtlar, soatlar (4 tadan), ertalabki reja, bekor qilish."""
    relative = [o for o in options if not o[0].isdigit()]
    clocks = [o for o in options if o[0].isdigit()]
    rows = []
    if relative:
        rows.append([KeyboardButton(text=o) for o in relative])
    if clocks:
        rows.append([KeyboardButton(text=o) for o in clocks])
    if with_morning:
        rows.append([KeyboardButton(text=MORNING)])
    rows.append([KeyboardButton(text=CANCEL)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def tasks_keyboard(
    tasks: list[Task], page: int, pages: int, start_number: int, done_count: int = 0
) -> InlineKeyboardMarkup:
    """Ro'yxat ostida: vazifa raqamlari (5 tadan qatorda), sahifalash va tozalash.

    Raqam bosilganda vazifa kartasi ochiladi — har bir vazifa uchun ikkita tugma o'rniga bitta.
    """
    builder = InlineKeyboardBuilder()
    sizes = []
    for number, task in enumerate(tasks, start=start_number):
        builder.button(
            text=str(number), callback_data=TaskCallback(action='open', task_id=task.id, page=page)
        )
    full, rest = divmod(len(tasks), NUMBERS_PER_ROW)
    sizes += [NUMBERS_PER_ROW] * full + ([rest] if rest else [])

    if pages > 1:
        nav = 0
        if page > 0:
            builder.button(text='◀️', callback_data=PageCallback(page=page - 1))
            nav += 1
        builder.button(text=f'{page + 1}/{pages}', callback_data=PageCallback(page=page))
        nav += 1
        if page < pages - 1:
            builder.button(text='▶️', callback_data=PageCallback(page=page + 1))
            nav += 1
        sizes.append(nav)

    if done_count:
        builder.button(
            text=f'🧹 Bajarilganlarni tozalash ({done_count})', callback_data=ClearDoneCallback()
        )
        sizes.append(1)

    builder.adjust(*sizes)
    return builder.as_markup()


def task_card_keyboard(task_id: int, page: int, important: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, action in [
        ('✅ Bajarildi', 'done'),
        ('☆ Oddiy qilish' if important else '⭐ Muhim', 'star'),
        ("⏰ Vaqtini o'zgartirish", 'edit'),
        ("✏️ Nomini o'zgartirish", 'rename'),
        ('📅 Ertaga', 'tomorrow'),
        ("🗑 O'chirish", 'delete'),
    ]:
        builder.button(
            text=text, callback_data=TaskCallback(action=action, task_id=task_id, page=page)
        )
    builder.button(text="◀️ Ro'yxatga qaytish", callback_data=PageCallback(page=page))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()
