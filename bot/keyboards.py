from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import Task

ADD_TASK = "➕ Vazifa qo'shish"
MY_TASKS = '📋 Vazifalarim'
STATS = '📊 Statistika'
TODAY_PLAN = '☀️ Bugungi reja'
CANCEL = '❌ Bekor qilish'
TODAY = 'Bugun'
TOMORROW = 'Ertaga'
NO_DUE = '⏭ Muddatsiz'
EVERY_DAY = '🔁 Har kuni'

# Menyu tugmalari — vazifa nomi sifatida qabul qilinmaydi
MENU_BUTTONS = {ADD_TASK, MY_TASKS, STATS, TODAY_PLAN, CANCEL}

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_TASK)],
        [KeyboardButton(text=MY_TASKS), KeyboardButton(text=TODAY_PLAN)],
        [KeyboardButton(text=STATS)],
    ],
    resize_keyboard=True,
)

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL)]],
    resize_keyboard=True,
)


due_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=TODAY), KeyboardButton(text=TOMORROW)],
        [KeyboardButton(text=EVERY_DAY), KeyboardButton(text=NO_DUE)],
        [KeyboardButton(text=CANCEL)],
    ],
    resize_keyboard=True,
)


class TaskCallback(CallbackData, prefix='task'):
    action: str  # 'done' | 'delete'
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


SNOOZE_OPTIONS = [('+15 daq', 15), ('+1 soat', 60), ('Ertaga', 0)]


def remind_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Bajarildi', callback_data=RemindCallback(task_id=task_id))
    for text, minutes in SNOOZE_OPTIONS:
        builder.button(
            text=f'⏰ {text}', callback_data=SnoozeCallback(task_id=task_id, minutes=minutes)
        )
    builder.adjust(1, 3)
    return builder.as_markup()


def tasks_keyboard(
    tasks: list[Task], page: int, pages: int, start_number: int, has_done: bool = False
) -> InlineKeyboardMarkup:
    """Har bir vazifa uchun bitta qator: [✅ N] [🗑 N]; pastda sahifalash va tozalash."""
    builder = InlineKeyboardBuilder()
    sizes = []
    for number, task in enumerate(tasks, start=start_number):
        if not task.is_done:
            builder.button(
                text=f'✅ {number}',
                callback_data=TaskCallback(action='done', task_id=task.id, page=page),
            )
        builder.button(
            text=f'🗑 {number}',
            callback_data=TaskCallback(action='delete', task_id=task.id, page=page),
        )
        sizes.append(1 if task.is_done else 2)

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

    if has_done:
        builder.button(text='🧹 Bajarilganlarni tozalash', callback_data=ClearDoneCallback())
        sizes.append(1)

    builder.adjust(*sizes)
    return builder.as_markup()
