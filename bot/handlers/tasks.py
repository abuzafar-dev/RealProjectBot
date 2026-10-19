from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import ADD_TASK, MY_TASKS, TaskCallback, cancel_menu, main_menu, task_buttons
from bot.loader import db
from bot.states import AddTask

router = Router()


@router.message(F.text == ADD_TASK)
async def add_task_start(message: Message, state: FSMContext):
    await state.set_state(AddTask.title)
    await message.answer('Vazifa nomini yozing:', reply_markup=cancel_menu)


@router.message(AddTask.title, F.text)
async def add_task_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) > 200:
        await message.answer("Vazifa nomi 200 belgidan oshmasin. Qaytadan yozing:")
        return
    db.add_user(message.from_user.id, message.from_user.full_name)
    db.add_task(message.from_user.id, title)
    await state.clear()
    await message.answer(f"✅ Qo'shildi: {html.quote(title)}", reply_markup=main_menu)


@router.message(AddTask.title)
async def add_task_wrong(message: Message):
    await message.answer('Iltimos, vazifa nomini matn ko\'rinishida yozing')


@router.message(F.text == MY_TASKS)
async def my_tasks(message: Message):
    tasks = db.get_tasks(message.from_user.id)
    if not tasks:
        await message.answer("Sizda hali vazifa yo'q")
        return
    for task in tasks:
        status = '✅' if task['is_done'] else '🕐'
        await message.answer(f"{status} {html.quote(task['title'])}", reply_markup=task_buttons(task))


@router.callback_query(TaskCallback.filter(F.action == 'done'))
async def task_done(callback: CallbackQuery, callback_data: TaskCallback):
    task = db.get_task(callback_data.task_id, callback.from_user.id)
    if task is None:
        await callback.answer('Vazifa topilmadi', show_alert=True)
        return
    db.mark_done(task['id'], callback.from_user.id)
    task = db.get_task(task['id'], callback.from_user.id)
    await callback.message.edit_text(f"✅ {html.quote(task['title'])}", reply_markup=task_buttons(task))
    await callback.answer('Bajarildi deb belgilandi')


@router.callback_query(TaskCallback.filter(F.action == 'delete'))
async def task_delete(callback: CallbackQuery, callback_data: TaskCallback):
    if db.delete_task(callback_data.task_id, callback.from_user.id):
        await callback.message.delete()
        await callback.answer("O'chirildi")
    else:
        await callback.answer('Vazifa topilmadi', show_alert=True)
