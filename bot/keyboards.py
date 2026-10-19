from aiogram.filters.callback_data import CallbackData
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

ADD_TASK = "➕ Vazifa qo'shish"
MY_TASKS = '📋 Vazifalarim'
STATS = '📊 Statistika'
CANCEL = '❌ Bekor qilish'

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_TASK)],
        [KeyboardButton(text=MY_TASKS), KeyboardButton(text=STATS)],
    ],
    resize_keyboard=True,
)

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL)]],
    resize_keyboard=True,
)


class TaskCallback(CallbackData, prefix='task'):
    action: str
    task_id: int


def task_buttons(task):
    builder = InlineKeyboardBuilder()
    if not task['is_done']:
        builder.button(text='✅ Bajarildi', callback_data=TaskCallback(action='done', task_id=task['id']))
    builder.button(text="🗑 O'chirish", callback_data=TaskCallback(action='delete', task_id=task['id']))
    return builder.as_markup()
