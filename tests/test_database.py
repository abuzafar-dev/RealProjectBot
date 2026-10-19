import pytest

from bot.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / 'test.db')
    database.add_user(1, 'Ali')
    database.add_user(2, 'Vali')
    return database


def test_add_and_get_tasks(db):
    db.add_task(1, 'Kitob o\'qish')
    db.add_task(1, 'Sport')
    assert len(db.get_tasks(1)) == 2
    assert db.get_tasks(2) == []


def test_mark_done_and_stats(db):
    db.add_task(1, 'Dars')
    task_id = db.get_tasks(1)[0]['id']
    db.mark_done(task_id, 1)
    assert db.get_stats(1) == (1, 1)


def test_user_cannot_touch_other_tasks(db):
    db.add_task(1, 'Dars')
    task_id = db.get_tasks(1)[0]['id']
    assert db.delete_task(task_id, 2) == 0
    assert db.mark_done(task_id, 2) == 0
    assert db.get_task(task_id, 2) is None
    assert len(db.get_tasks(1)) == 1


def test_add_user_twice(db):
    db.add_user(1, 'Ali Valiyev')
    assert db.count_users() == 2
