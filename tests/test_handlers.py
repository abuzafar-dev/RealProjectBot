import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.handlers import tasks
from bot.handlers.start import stats_handler
from bot.keyboards import TaskCallback
from bot.loader import db


def make_message(text='', user_id=100):
    message = AsyncMock()
    message.text = text
    message.from_user = MagicMock(id=user_id, full_name='Test User')
    return message


def test_add_task_flow():
    state = AsyncMock()
    asyncio.run(tasks.add_task_title(make_message('<b>Ingliz tili</b>'), state))
    state.clear.assert_called_once()
    titles = [task['title'] for task in db.get_tasks(100)]
    assert '<b>Ingliz tili</b>' in titles


def test_long_title_rejected():
    state = AsyncMock()
    message = make_message('a' * 201, user_id=101)
    asyncio.run(tasks.add_task_title(message, state))
    state.clear.assert_not_called()
    assert db.get_tasks(101) == []


def test_done_callback():
    db.add_user(102, 'Test')
    db.add_task(102, 'Yugurish')
    task_id = db.get_tasks(102)[0]['id']
    callback = AsyncMock()
    callback.from_user = MagicMock(id=102)
    asyncio.run(tasks.task_done(callback, TaskCallback(action='done', task_id=task_id)))
    assert db.get_task(task_id, 102)['is_done'] == 1


def test_stats():
    db.add_user(103, 'Test')
    db.add_task(103, 'Bir')
    message = make_message(user_id=103)
    asyncio.run(stats_handler(message))
    assert 'Jami vazifalar: 1' in message.answer.call_args.args[0]
