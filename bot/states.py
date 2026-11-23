from aiogram.fsm.state import State, StatesGroup


class AddTask(StatesGroup):
    title = State()
    day = State()  # qaysi kun (yoki to'liq muddat: "ertaga 15:00")
    time = State()  # soat nechada eslatish


class RenameTask(StatesGroup):
    title = State()
