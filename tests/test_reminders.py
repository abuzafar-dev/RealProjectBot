from datetime import date, datetime, time
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from aiogram.methods import SendMessage

from bot.reminders import tick
from tests.conftest import NOW

DIGEST_HOUR = 8


@pytest.fixture
async def user(db):
    await db.add_user(1, 'Ali')
    return 1


@pytest.fixture
def bot():
    return AsyncMock()


def sent_texts(bot):
    return [call.args[1] for call in bot.send_message.call_args_list]


async def test_reminder_sent_once_when_time_comes(db, user, bot, clock):
    await db.add_task(user, 'Hisobot', date(2026, 11, 20), time(10, 30))

    await tick(bot, db, clock, DIGEST_HOUR)  # 10:00 — hali erta
    assert not any('Eslatma' in t for t in sent_texts(bot))

    clock.current = datetime(2026, 11, 20, 10, 30)
    await tick(bot, db, clock, DIGEST_HOUR)
    await tick(bot, db, clock, DIGEST_HOUR)  # qayta tekshiruv — ikkinchi marta kelmaydi
    reminders = [t for t in sent_texts(bot) if 'Eslatma' in t]
    assert len(reminders) == 1 and 'Hisobot' in reminders[0]


async def test_missed_reminder_sent_after_restart(db, user, bot, clock):
    # bot o'chiq turganda vaqti o'tib ketgan eslatma ishga tushganda yuboriladi
    await db.add_task(user, 'Qo‘ng‘iroq', date(2026, 11, 19), time(18, 0))
    await tick(bot, db, clock, DIGEST_HOUR)
    assert any('Eslatma' in t for t in sent_texts(bot))


async def test_done_task_not_reminded(db, user, bot, clock):
    task_id = await db.add_task(user, 'Hisobot', date(2026, 11, 20), time(9, 0))
    await db.mark_done(task_id, user)
    await tick(bot, db, clock, DIGEST_HOUR)
    assert not any('Eslatma' in t for t in sent_texts(bot))


async def test_digest_once_per_day(db, user, bot, clock):
    await db.add_task(user, 'Bugungi', date(2026, 11, 20))
    await db.add_task(user, 'Kechagi', date(2026, 11, 19))
    await db.add_task(user, 'Ertangi', date(2026, 11, 21))
    await db.add_task(user, 'Muddatsiz')

    clock.current = datetime(2026, 11, 20, 7, 59)
    await tick(bot, db, clock, DIGEST_HOUR)
    assert bot.send_message.await_count == 0  # soat 8 bo'lmagan

    clock.current = NOW
    await tick(bot, db, clock, DIGEST_HOUR)
    await tick(bot, db, clock, DIGEST_HOUR)
    [digest] = sent_texts(bot)
    assert 'Bugungi' in digest and 'Kechagi' in digest
    assert "Muddati o'tgan" in digest
    assert 'Ertangi' not in digest and 'Muddatsiz' not in digest

    clock.current = datetime(2026, 11, 21, 8, 0)  # ertasi kuni yana keladi
    await tick(bot, db, clock, DIGEST_HOUR)
    assert bot.send_message.await_count == 2


async def test_no_digest_without_due_tasks(db, user, bot, clock):
    await db.add_task(user, 'Muddatsiz')
    await tick(bot, db, clock, DIGEST_HOUR)
    bot.send_message.assert_not_awaited()


async def test_blocked_user_does_not_break_others(db, bot, clock):
    await db.add_user(1, 'Ali')
    await db.add_user(2, 'Vali')
    await db.add_task(1, 'A', date(2026, 11, 20), time(9, 0))
    await db.add_task(2, 'B', date(2026, 11, 20), time(9, 0))

    async def send(chat_id, text, **kwargs):
        if chat_id == 1:
            raise TelegramForbiddenError(SendMessage(chat_id=1, text=text), 'blocked')

    bot.send_message.side_effect = send
    await tick(bot, db, clock, DIGEST_HOUR)
    await tick(bot, db, clock, DIGEST_HOUR)
    # 1-foydalanuvchiga qayta urinilmaydi, 2-chisiga eslatma ham, reja ham bir marta yetadi
    calls = [call.args[0] for call in bot.send_message.call_args_list]
    assert calls.count(1) == 2 and calls.count(2) == 2  # eslatma + reja


async def test_bad_chat_does_not_block_queue(db, bot, clock):
    # "chat not found" kabi doimiy xato bitta vazifada bo'lsa, qolgan eslatmalar tiqilib qolmasin
    await db.add_user(1, 'Ali')
    await db.add_user(2, 'Vali')
    await db.add_task(1, 'A', date(2026, 11, 20), time(9, 0))
    await db.add_task(2, 'B', date(2026, 11, 20), time(9, 30))

    async def send(chat_id, text, **kwargs):
        if chat_id == 1:
            raise TelegramBadRequest(SendMessage(chat_id=1, text=text), 'chat not found')

    bot.send_message.side_effect = send
    await tick(bot, db, clock, DIGEST_HOUR)
    await tick(bot, db, clock, DIGEST_HOUR)
    calls = [call.args[0] for call in bot.send_message.call_args_list]
    assert calls.count(1) == 2  # eslatma + reja, keyin qayta urinilmaydi
    assert calls.count(2) == 2


async def test_network_error_retried_without_blocking_others(db, bot, clock):
    await db.add_user(1, 'Ali')
    await db.add_user(2, 'Vali')
    await db.add_task(1, 'A', date(2026, 11, 20), time(9, 0))
    await db.add_task(2, 'B', date(2026, 11, 20), time(9, 30))
    fail = {'on': True}

    async def send(chat_id, text, **kwargs):
        if chat_id == 1 and fail['on']:
            raise TelegramNetworkError(SendMessage(chat_id=1, text=text), 'timeout')

    bot.send_message.side_effect = send
    await tick(bot, db, clock, DIGEST_HOUR)
    assert any(c.args[0] == 2 and 'Eslatma' in c.args[1] for c in bot.send_message.call_args_list)

    fail['on'] = False  # tarmoq tiklandi — 1-foydalanuvchiga eslatma qayta yuboriladi
    await tick(bot, db, clock, DIGEST_HOUR)
    reminders_to_1 = [
        c for c in bot.send_message.call_args_list if c.args[0] == 1 and 'Eslatma' in c.args[1]
    ]
    assert len(reminders_to_1) == 2  # 1-urinish (xato) + qayta yuborish
