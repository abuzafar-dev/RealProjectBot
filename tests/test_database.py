from datetime import date, time

import aiosqlite
import pytest

from bot.database import Database


@pytest.fixture
async def users(db):
    await db.add_user(1, 'Ali')
    await db.add_user(2, 'Vali')
    return db


async def test_add_and_get_tasks(users):
    await users.add_task(1, "Kitob o'qish")
    await users.add_task(1, 'Sport')
    tasks = await users.get_tasks(1)
    assert [t.title for t in tasks] == ['Sport', "Kitob o'qish"]  # yangisi tepada
    assert await users.get_tasks(2) == []


async def test_done_tasks_go_last(users):
    first = await users.add_task(1, 'Birinchi')
    await users.add_task(1, 'Ikkinchi')
    await users.mark_done(first, 1)
    tasks = await users.get_tasks(1)
    assert [t.title for t in tasks] == ['Ikkinchi', 'Birinchi']
    assert tasks[-1].is_done and tasks[-1].done_at is not None


async def test_pagination(users):
    for i in range(15):
        await users.add_task(1, f'Vazifa {i}')
    page = await users.get_tasks(1, limit=10, offset=10)
    assert len(page) == 5


async def test_mark_done_and_stats(users):
    task_id = await users.add_task(1, 'Dars')
    await users.add_task(1, 'Sport')
    assert await users.mark_done(task_id, 1) is True
    assert await users.mark_done(task_id, 1) is False  # qayta belgilab bo'lmaydi
    stats = await users.get_stats(1)
    assert (stats.total, stats.done, stats.left, stats.percent) == (2, 1, 1, 50)


async def test_empty_stats(users):
    stats = await users.get_stats(1)
    assert (stats.total, stats.done, stats.percent) == (0, 0, 0)


async def test_user_cannot_touch_other_tasks(users):
    task_id = await users.add_task(1, 'Dars')
    assert await users.delete_task(task_id, 2) is False
    assert await users.mark_done(task_id, 2) is False
    assert await users.get_task(task_id, 2) is None
    assert len(await users.get_tasks(1)) == 1


async def test_add_user_twice_updates_name(users):
    await users.add_user(1, 'Ali Valiyev')
    assert await users.count_users() == 2


async def test_task_requires_existing_user(db):
    with pytest.raises(aiosqlite.IntegrityError):
        await db.add_task(999, 'Egasiz vazifa')


async def test_migrates_old_schema(tmp_path):
    path = tmp_path / 'old.db'
    async with aiosqlite.connect(path) as conn:
        await conn.executescript(
            'CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL,'
            ' created_at TEXT DEFAULT CURRENT_TIMESTAMP);'
            'CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,'
            ' title TEXT NOT NULL, is_done INTEGER DEFAULT 0,'
            ' created_at TEXT DEFAULT CURRENT_TIMESTAMP);'
            "INSERT INTO users (id, full_name) VALUES (1, 'Ali');"
            "INSERT INTO tasks (user_id, title) VALUES (1, 'Eski vazifa');"
        )
    database = Database(path)
    await database.connect()
    try:
        task = (await database.get_tasks(1))[0]
        assert task.title == 'Eski vazifa'
        assert await database.mark_done(task.id, 1) is True
        # yangi ustunlar qo'shilgan va ishlaydi
        new_id = await database.add_task(1, 'Yangi', date(2026, 12, 1), time(9, 0))
        assert (await database.get_task(new_id, 1)).due_time == time(9, 0)
    finally:
        await database.close()
