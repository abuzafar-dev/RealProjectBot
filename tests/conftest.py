from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot.database import Database

NOW = datetime(2026, 11, 20, 10, 0)  # juma, 10:00


class FakeClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def state() -> FSMContext:
    return FSMContext(MemoryStorage(), StorageKey(bot_id=1, chat_id=1, user_id=1))


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
