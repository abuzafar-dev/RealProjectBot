from unittest.mock import AsyncMock

import pytest

from bot.handlers import start, tasks
from bot.keyboards import PageCallback, TaskCallback


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


async def test_add_task_flow(db, make_message):
    state = AsyncMock()
    message = make_message('  <b>Ingliz   tili</b>  ')
    await tasks.add_task_title(message, state, db)
    state.clear.assert_awaited_once()
    assert [t.title for t in await db.get_tasks(1)] == ['<b>Ingliz tili</b>']
    # HTML foydalanuvchiga xavfsiz ko'rinishda qaytadi
    assert '&lt;b&gt;' in message.answer.call_args.args[0]


@pytest.mark.parametrize('text', ['a' * 201, '   '])
async def test_invalid_title_rejected(db, make_message, text):
    state = AsyncMock()
    await tasks.add_task_title(make_message(text), state, db)
    state.clear.assert_not_called()
    assert await db.get_tasks(1) == []


async def test_my_tasks_empty(db, make_message):
    message = make_message()
    await tasks.my_tasks(message, db)
    assert message.answer.call_args.args[0] == tasks.EMPTY_TEXT


async def test_my_tasks_single_message_with_buttons(db, user, make_message):
    await db.add_task(user, 'Yugurish')
    done_id = await db.add_task(user, 'Kitob')
    await db.mark_done(done_id, user)

    message = make_message(user_id=user)
    await tasks.my_tasks(message, db)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert '1. 🕐 Yugurish' in text
    assert '2. ✅ <s>Kitob</s>' in text
    markup = message.answer.call_args.kwargs['reply_markup']
    assert buttons(markup) == ['✅ 1', '🗑 1', '🗑 2']  # bajarilganda ✅ tugmasi yo'q


async def test_pagination_buttons(db, user):
    for i in range(tasks.PAGE_SIZE + 3):
        await db.add_task(user, f'Vazifa {i}')

    _, first = await tasks.render_tasks(db, user, page=0)
    assert buttons(first)[-2:] == ['1/2', '▶️']

    text, last = await tasks.render_tasks(db, user, page=5)  # chegaradan tashqari -> oxirgi
    assert buttons(last)[-2:] == ['◀️', '2/2']
    assert text.count('🕐') == 3


async def test_done_callback(db, user, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    callback = make_callback(user)
    await tasks.task_done(callback, TaskCallback(action='done', task_id=task_id), db)
    assert (await db.get_task(task_id, user)).is_done
    assert '✅ <s>Yugurish</s>' in callback.message.edit_text.call_args.args[0]


async def test_delete_callback(db, user, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    callback = make_callback(user)
    await tasks.task_delete(callback, TaskCallback(action='delete', task_id=task_id), db)
    assert await db.get_task(task_id, user) is None
    callback.message.edit_text.assert_awaited_once_with(tasks.EMPTY_TEXT, reply_markup=None)


async def test_foreign_callback_rejected(db, user, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    stranger = make_callback(user_id=777)
    await tasks.task_delete(stranger, TaskCallback(action='delete', task_id=task_id), db)
    assert await db.get_task(task_id, user) is not None
    assert stranger.answer.call_args.kwargs.get('show_alert') is True


async def test_change_page(db, user, make_callback):
    for i in range(tasks.PAGE_SIZE + 1):
        await db.add_task(user, f'Vazifa {i}')
    callback = make_callback(user)
    await tasks.change_page(callback, PageCallback(page=1), db)
    assert '11. 🕐' in callback.message.edit_text.call_args.args[0]


async def test_stats(db, user, make_message):
    task_id = await db.add_task(user, 'Bir')
    await db.add_task(user, 'Ikki')
    await db.mark_done(task_id, user)
    message = make_message(user_id=user)
    await start.stats_handler(message, db)
    text = message.answer.call_args.args[0]
    assert 'Jami vazifalar: 2' in text
    assert '50%' in text
