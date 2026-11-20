from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.database import Database


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / 'test.db')
    await database.connect()
    yield database
    await database.close()


def make_user(user_id: int = 1, full_name: str = 'Test User') -> MagicMock:
    return MagicMock(id=user_id, full_name=full_name)


@pytest.fixture
def make_message():
    def factory(text: str = '', user_id: int = 1) -> AsyncMock:
        message = AsyncMock()
        message.text = text
        message.from_user = make_user(user_id)
        return message

    return factory


@pytest.fixture
def make_callback():
    def factory(user_id: int = 1) -> AsyncMock:
        callback = AsyncMock()
        callback.from_user = make_user(user_id)
        return callback

    return factory
