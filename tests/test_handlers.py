from datetime import date, time
from unittest.mock import AsyncMock

import pytest

from bot.handlers import start, tasks
from bot.keyboards import NO_DUE, PageCallback, RemindCallback, TaskCallback
from bot.states import AddTask
from tests.conftest import NOW

TODAY = NOW.date()


@pytest.fixture
async def user(db):
    await db.add_user(1, 'Test User')
    return 1


def buttons(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_start_registers_user(db, make_message):
    message = make_message('/start', user_id=5)
    await start.start_handler(message, AsyncMock(), db)
    assert await db.count_users() == 1
    assert 'Test User' in message.answer.call_args.args[0]


async def add_flow(state, db, clock, make_message, title, due):
    await tasks.add_task_title(make_message(title), state)
    message = make_message(due)
    await tasks.add_task_due(message, state, db, clock)
    return message


async def test_add_task_without_due(db, state, clock, make_message):
    message = await add_flow(state, db, clock, make_message, '  <b>Ingliz   tili</b>  ', NO_DUE)
    assert await state.get_state() is None
    [task] = await db.get_tasks(1)
    assert task.title == '<b>Ingliz tili</b>' and task.due_date is None
    # HTML foydalanuvchiga xavfsiz ko'rinishda qaytadi
    assert '&lt;b&gt;' in message.answer.call_args.args[0]


async def test_add_task_with_time(db, state, clock, make_message):
    message = await add_flow(state, db, clock, make_message, 'Hisobot', 'ertaga 15:00')
    [task] = await db.get_tasks(1)
    assert (task.due_date, task.due_time) == (date(2026, 11, 21), time(15, 0))
    assert 'ertaga 15:00 da eslataman' in message.answer.call_args.args[0]


async def test_bad_due_keeps_state(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Hisobot'), state)
    message = make_message('kecha')
    await tasks.add_task_due(message, state, db, clock)
    assert await state.get_state() == AddTask.due  # qayta yozishi mumkin
    assert await db.get_tasks(1) == []
    assert 'tushunmadim' in message.answer.call_args.args[0]


@pytest.mark.parametrize('text', ['a' * 201, '   '])
async def test_invalid_title_rejected(state, make_message, text):
    await tasks.add_task_title(make_message(text), state)
    assert await state.get_state() is None


async def test_my_tasks_empty(db, clock, make_message):
    message = make_message()
    await tasks.my_tasks(message, db, clock)
    assert message.answer.call_args.args[0] == tasks.EMPTY_TEXT


async def test_my_tasks_single_message_with_buttons(db, user, clock, make_message):
    await db.add_task(user, 'Yugurish')
    done_id = await db.add_task(user, 'Kitob')
    await db.mark_done(done_id, user)

    message = make_message(user_id=user)
    await tasks.my_tasks(message, db, clock)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert '1. 🕐 Yugurish' in text
    assert '2. ✅ <s>Kitob</s>' in text
    markup = message.answer.call_args.kwargs['reply_markup']
    assert buttons(markup) == ['✅ 1', '🗑 1', '🗑 2']  # bajarilganda ✅ tugmasi yo'q


async def test_pagination_buttons(db, user):
    for i in range(tasks.PAGE_SIZE + 3):
        await db.add_task(user, f'Vazifa {i}')

    _, first = await tasks.render_tasks(db, user, 0, TODAY)
    assert buttons(first)[-2:] == ['1/2', '▶️']

    text, last = await tasks.render_tasks(db, user, 5, TODAY)  # chegaradan tashqari -> oxirgi
    assert buttons(last)[-2:] == ['◀️', '2/2']
    assert text.count('🕐') == 3


async def test_done_callback(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    callback = make_callback(user)
    await tasks.task_done(callback, TaskCallback(action='done', task_id=task_id), db, clock)
    assert (await db.get_task(task_id, user)).is_done
    assert '✅ <s>Yugurish</s>' in callback.message.edit_text.call_args.args[0]


async def test_delete_callback(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    callback = make_callback(user)
    await tasks.task_delete(callback, TaskCallback(action='delete', task_id=task_id), db, clock)
    assert await db.get_task(task_id, user) is None
    callback.message.edit_text.assert_awaited_once_with(tasks.EMPTY_TEXT, reply_markup=None)


async def test_foreign_callback_rejected(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    stranger = make_callback(user_id=777)
    await tasks.task_delete(stranger, TaskCallback(action='delete', task_id=task_id), db, clock)
    assert await db.get_task(task_id, user) is not None
    assert stranger.answer.call_args.kwargs.get('show_alert') is True


async def test_change_page(db, user, clock, make_callback):
    for i in range(tasks.PAGE_SIZE + 1):
        await db.add_task(user, f'Vazifa {i}')
    callback = make_callback(user)
    await tasks.change_page(callback, PageCallback(page=1), db, clock)
    assert '11. 🕐' in callback.message.edit_text.call_args.args[0]


async def test_stats(db, user, clock, make_message):
    task_id = await db.add_task(user, 'Bir')
    await db.add_task(user, 'Ikki', due_date=date(2026, 11, 19))  # kecha — muddati o'tgan
    await db.mark_done(task_id, user)
    message = make_message(user_id=user)
    await start.stats_handler(message, db, clock)
    text = message.answer.call_args.args[0]
    assert 'Jami vazifalar: 2' in text
    assert "Muddati o'tgan: 1" in text
    assert '50%' in text


async def test_list_shows_due_and_overdue(db, user):
    await db.add_task(user, 'Muddatsiz')
    await db.add_task(user, 'Ertangi', due_date=date(2026, 11, 21), due_time=time(9, 0))
    await db.add_task(user, 'Kechagi', due_date=date(2026, 11, 19))
    text, _ = await tasks.render_tasks(db, user, 0, TODAY)
    # eng yaqin muddat tepada, muddatsiz pastda
    assert '1. 🕐 Kechagi — ⚠️ 19.11' in text
    assert '2. 🕐 Ertangi — 📅 ertaga 09:00' in text
    assert '3. 🕐 Muddatsiz' in text


async def test_remind_done_button(db, user, make_callback):
    task_id = await db.add_task(user, 'Hisobot')
    callback = make_callback(user)
    await tasks.remind_done(callback, RemindCallback(task_id=task_id), db)
    assert (await db.get_task(task_id, user)).is_done
    assert '<s>Hisobot</s>' in callback.message.edit_text.call_args.args[0]
