from datetime import date, datetime, time
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendPhoto

from bot import texts
from bot.handlers import settings, start, tasks
from bot.keyboards import (
    MORNING,
    MY_TASKS,
    NO_DUE,
    PageCallback,
    RemindCallback,
    SettingsCallback,
    SnoozeCallback,
    TaskCallback,
)
from bot.states import AddTask
from tests.conftest import NOW

TODAY = NOW.date()


@pytest.fixture
async def user(db):
    await db.add_user(1, 'Test User')
    return 1


def buttons(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_start_registers_user_and_sends_welcome_photo(db, make_message):
    message = make_message('/start', user_id=5)
    await start.start_handler(message, AsyncMock(), db)
    assert await db.count_users() == 1
    caption = message.answer_photo.call_args.kwargs['caption']
    assert 'Test User' in caption and '/help' in caption
    assert len(caption) <= 1024  # Telegram izoh chegarasi


async def test_start_falls_back_to_text_if_photo_fails(db, make_message):
    message = make_message('/start')
    message.answer_photo.side_effect = TelegramBadRequest(SendPhoto(chat_id=1, photo='x'), 'bad')
    await start.start_handler(message, AsyncMock(), db)
    assert 'Test User' in message.answer.call_args.args[0]


def test_profile_texts_fit_telegram_limits():
    assert len(texts.DESCRIPTION) <= 512
    assert len(texts.SHORT_DESCRIPTION) <= 120
    assert texts.WELCOME_IMAGE.exists()


async def add_flow(state, db, clock, make_message, title, due):
    await tasks.add_task_title(make_message(title), state, db, clock)
    message = make_message(due)
    await tasks.add_task_day(message, state, db, clock)
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
    assert 'ertaga 15:00 — aynan shu vaqtda eslataman' in message.answer.call_args.args[0]


async def test_bad_due_keeps_state(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Hisobot'), state, db, clock)
    message = make_message('kecha')
    await tasks.add_task_day(message, state, db, clock)
    assert await state.get_state() == AddTask.day  # qayta yozishi mumkin
    assert await db.get_tasks(1) == []
    assert 'tushunmadim' in message.answer.call_args.args[0]


@pytest.mark.parametrize('text', ['a' * 201, '   ', 'ab', '12345', '...!!!', '😀😀😀'])
async def test_invalid_title_rejected(db, state, clock, make_message, text):
    await tasks.add_task_title(make_message(text), state, db, clock)
    assert await state.get_state() is None


async def test_my_tasks_empty(db, state, clock, make_message):
    message = make_message()
    await tasks.my_tasks(message, state, db, clock)
    assert message.answer.call_args.args[0] == tasks.EMPTY_TEXT


async def test_my_tasks_single_message_with_buttons(db, user, state, clock, make_message):
    await db.add_task(user, 'Yugurish')
    done_id = await db.add_task(user, 'Kitob')
    await db.mark_done(done_id, user)

    message = make_message(user_id=user)
    await tasks.my_tasks(message, state, db, clock)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert '1. Yugurish' in text
    assert 'Kitob' not in text  # bajarilgan ro'yxatni egallamaydi — faqat soni
    assert '✅ Bajarilgan: 1 ta' in text
    markup = message.answer.call_args.kwargs['reply_markup']
    assert buttons(markup) == ['1', '🧹 Bajarilganlarni tozalash (1)']


async def test_pagination_buttons(db, user):
    for i in range(tasks.PAGE_SIZE + 3):
        await db.add_task(user, f'Vazifa {i}')

    _, first = await tasks.render_tasks(db, user, 0, TODAY)
    rows = [[b.text for b in row] for row in first.inline_keyboard]
    assert rows[:2] == [['1', '2', '3', '4', '5'], ['6', '7', '8', '9', '10']]
    assert rows[-1] == ['1/2', '▶️']

    text, last = await tasks.render_tasks(db, user, 5, TODAY)  # chegaradan tashqari -> oxirgi
    assert buttons(last)[-2:] == ['◀️', '2/2']
    assert '13. Vazifa 0' in text and '10.' not in text


async def test_done_callback(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Yugurish')
    await db.add_task(user, 'Kitob')
    callback = make_callback(user)
    await tasks.task_done(callback, TaskCallback(action='done', task_id=task_id), db, clock)
    assert (await db.get_task(task_id, user)).is_done
    text = callback.message.edit_text.call_args.args[0]
    assert 'Yugurish' not in text and '✅ Bajarilgan: 1 ta' in text


async def test_open_task_card(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot', date(2026, 11, 18), repeat='daily')
    callback = make_callback(user)
    await tasks.task_open(callback, TaskCallback(action='open', task_id=task_id, page=0), db, clock)
    text = callback.message.edit_text.call_args.args[0]
    assert '<b>Hisobot</b>' in text and '2 kun oldin' in text and 'har kuni' in text
    markup = callback.message.edit_text.call_args.kwargs['reply_markup']
    assert buttons(markup) == [
        '✅ Bajarildi',
        "⏰ Vaqtini o'zgartirish",
        "✏️ Nomini o'zgartirish",
        '📅 Ertaga',
        "🗑 O'chirish",
        "◀️ Ro'yxatga qaytish",
    ]


async def test_move_to_tomorrow_keeps_time(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot', date(2026, 11, 18), time(9, 0))
    callback = make_callback(user)
    data = TaskCallback(action='tomorrow', task_id=task_id)
    await tasks.task_tomorrow(callback, data, db, clock)
    task = await db.get_task(task_id, user)
    assert (task.due_date, task.due_time) == (date(2026, 11, 21), time(9, 0))


async def test_done_task_card_not_reopened(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot')
    await db.mark_done(task_id, user)
    callback = make_callback(user)
    await tasks.task_open(callback, TaskCallback(action='open', task_id=task_id), db, clock)
    assert callback.answer.call_args.kwargs.get('show_alert') is True


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
    assert '11. Vazifa' in callback.message.edit_text.call_args.args[0]


async def test_stats(db, user, clock, make_message):
    task_id = await db.add_task(user, 'Bir')
    await db.add_task(user, 'Ikki', due_date=date(2026, 11, 19))  # kecha — muddati o'tgan
    await db.mark_done(task_id, user, NOW)
    old = await db.add_task(user, 'Kechagi ish')
    await db.mark_done(old, user, datetime(2026, 11, 19, 21, 0))
    message = make_message(user_id=user)
    await start.stats_handler(message, db, clock)
    text = message.answer.call_args.args[0]
    assert 'Bugun bajarildi: 1' in text
    assert 'Shu hafta: 2' in text  # 16.11 dushanbadan beri
    assert '🔥 2 kun ketma-ket' in text
    assert 'Jami: 3 · bajarilgan 2 · qolgan 1' in text
    assert "Muddati o'tgan: 1" in text


async def test_list_grouped_by_sections(db, user):
    await db.add_task(user, 'Muddatsiz')
    await db.add_task(user, 'Ertangi', due_date=date(2026, 11, 21), due_time=time(9, 0))
    await db.add_task(user, 'Bugungi', due_date=TODAY, due_time=time(15, 0), repeat='daily')
    await db.add_task(user, 'Eski', due_date=date(2026, 11, 15))
    text, _ = await tasks.render_tasks(db, user, 0, TODAY)
    expected = [
        "⚠️ <b>Muddati o'tgan</b>",
        '1. Eski · 15.11',
        '📅 <b>Bugun</b>',
        '2. Bugungi · 15:00 🔁',
        '🗓 <b>Keyingi</b>',
        '3. Ertangi · ertaga 09:00',
        '📝 <b>Muddatsiz</b>',
        '4. Muddatsiz',
    ]
    positions = [text.index(line) for line in expected]
    assert positions == sorted(positions)


async def test_all_done_message(db, user):
    await db.mark_done(await db.add_task(user, 'A'), user)
    text, markup = await tasks.render_tasks(db, user, 0, TODAY)
    assert 'Hammasi bajarilgan' in text
    assert buttons(markup) == ['🧹 Bajarilganlarni tozalash (1)']


async def test_remind_done_button(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot')
    callback = make_callback(user)
    await tasks.remind_done(callback, RemindCallback(task_id=task_id), db, clock)
    assert (await db.get_task(task_id, user)).is_done
    assert '<s>Hisobot</s>' in callback.message.edit_text.call_args.args[0]


# --- topilgan xatolar uchun regressiya testlari ---


async def test_menu_button_is_not_saved_as_title(db, state, clock, make_message):
    await state.set_state(AddTask.title)
    message = make_message(MY_TASKS)
    await tasks.add_task_title(message, state, db, clock)
    assert await state.get_state() == AddTask.title  # nom hali ham kutilmoqda
    assert 'menyu tugmasi' in message.answer.call_args.args[0]


async def test_menu_button_cancels_add_flow(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Hisobot'), state, db, clock)
    await tasks.my_tasks(make_message(MY_TASKS), state, db, clock)
    assert await state.get_state() is None


async def test_quick_add_free_text(db, state, clock, make_message):
    await tasks.quick_add(make_message("Kitob o'qish"), state, db, clock)
    assert await state.get_state() == AddTask.day
    await tasks.add_task_day(make_message(NO_DUE), state, db, clock)
    [task] = await db.get_tasks(1)
    assert task.title == "Kitob o'qish"


# --- yangi imkoniyatlar ---


async def test_recurring_task_creates_next_on_done(
    db, user, state, clock, make_callback, make_message
):
    await add_flow(state, db, clock, make_message, 'Sport', 'har kuni 09:00')
    [task] = await db.get_tasks(user)
    # 10:00 da 09:00 o'tib ketgan — birinchisi ertaga
    assert (task.due_date, task.due_time, task.repeat) == (date(2026, 11, 21), time(9), 'daily')

    callback = make_callback(user)
    await tasks.remind_done(callback, RemindCallback(task_id=task.id), db, clock)
    assert 'Keyingisi' in callback.message.edit_text.call_args.args[0]
    open_tasks = [t for t in await db.get_tasks(user) if not t.is_done]
    assert [(t.due_date, t.repeat) for t in open_tasks] == [(date(2026, 11, 22), 'daily')]


async def test_snooze_reschedules_and_rearms_reminder(db, user, clock, make_callback):
    task_id = await db.add_task(user, "Qo'ng'iroq", TODAY, time(9, 30))
    await db.mark_reminded(task_id)
    callback = make_callback(user)
    await tasks.snooze(callback, SnoozeCallback(task_id=task_id, minutes=15), db, clock)
    task = await db.get_task(task_id, user)
    assert (task.due_date, task.due_time) == (TODAY, time(10, 15))
    assert [t.id for t in await db.get_due_reminders(NOW.replace(minute=15))] == [task_id]


async def test_snooze_tomorrow_keeps_time(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot', TODAY, time(9, 30))
    await tasks.snooze(make_callback(user), SnoozeCallback(task_id=task_id, minutes=0), db, clock)
    task = await db.get_task(task_id, user)
    assert (task.due_date, task.due_time) == (date(2026, 11, 21), time(9, 30))


async def test_snooze_foreign_task_rejected(db, user, clock, make_callback):
    task_id = await db.add_task(user, 'Hisobot', TODAY, time(9, 30))
    stranger = make_callback(user_id=777)
    await tasks.snooze(stranger, SnoozeCallback(task_id=task_id, minutes=15), db, clock)
    assert (await db.get_task(task_id, user)).due_time == time(9, 30)


async def test_clear_done(db, user, clock, make_callback):
    keep = await db.add_task(user, 'Qoladi')
    for title in ('A', 'B'):
        await db.mark_done(await db.add_task(user, title), user)
    callback = make_callback(user)
    await tasks.clear_done(callback, db, clock)
    assert [t.id for t in await db.get_tasks(user)] == [keep]
    assert '2 ta' in callback.answer.call_args.args[0]


async def test_today_plan(db, user, state, clock, make_message):
    message = make_message(user_id=user)
    await tasks.today_plan(message, state, db, clock)
    assert "vazifa yo'q" in message.answer.call_args.args[0]

    await db.add_task(user, 'Bugungi', TODAY)
    await tasks.today_plan(message, state, db, clock)
    assert 'Bugungi' in message.answer.call_args.args[0]


async def test_admin_only_for_owner(db, user, make_message):
    stranger = make_message('/admin', user_id=2)
    await start.admin_handler(stranger, db, admin_id=1)
    assert 'Admin' not in stranger.answer.call_args.args[0]

    owner = make_message('/admin', user_id=1)
    await start.admin_handler(owner, db, admin_id=1)
    assert 'Foydalanuvchilar: 1' in owner.answer.call_args.args[0]


# --- "qaysi kun → soat nechada" qadamlari: eslatma albatta yetib borishi kerak ---


def reply_buttons(message):
    markup = message.answer.call_args.kwargs['reply_markup']
    return [button.text for row in markup.keyboard for button in row]


async def test_day_only_asks_time(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Dars'), state, db, clock)
    message = make_message('Bugun')
    await tasks.add_task_day(message, state, db, clock)
    assert await state.get_state() == AddTask.time
    assert 'Soat nechada' in message.answer.call_args.args[0]
    assert await db.get_tasks(1) == []  # vaqt tanlanmaguncha saqlanmaydi


async def test_evening_today_offers_only_future_times(db, state, clock, make_message):
    # Skrinshotdagi holat: soat 20:07, «Bugun» — ertalabki reja o'tib ketgan
    clock.current = datetime(2026, 11, 20, 20, 7)
    await tasks.add_task_title(make_message('dars tugedi'), state, db, clock)
    message = make_message('Bugun')
    await tasks.add_task_day(message, state, db, clock)
    options = reply_buttons(message)
    assert '21:00' in options and '09:00' not in options and '18:00' not in options
    assert MORNING not in options  # eslatma yetib bormaydigan variant ko'rsatilmaydi

    refused = make_message(MORNING)
    await tasks.add_task_time(refused, state, db, clock)
    assert "o'tib ketgan" in refused.answer.call_args.args[0]
    assert await db.get_tasks(1) == []

    done = make_message('21:00')
    await tasks.add_task_time(done, state, db, clock)
    [task] = await db.get_tasks(1)
    assert (task.due_date, task.due_time) == (date(2026, 11, 20), time(21, 0))
    assert 'bugun 21:00 — aynan shu vaqtda eslataman' in done.answer.call_args.args[0]


async def test_relative_time(db, state, clock, make_message):
    await tasks.add_task_title(make_message("Qo'ng'iroq"), state, db, clock)
    await tasks.add_task_day(make_message('Bugun'), state, db, clock)
    await tasks.add_task_time(make_message('⏱ 1 soatdan keyin'), state, db, clock)
    [task] = await db.get_tasks(1)
    assert (task.due_date, task.due_time) == (TODAY, time(11, 0))


async def test_past_time_today_rejected(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Hisobot'), state, db, clock)
    await tasks.add_task_day(make_message('Bugun'), state, db, clock)
    message = make_message('09:00')  # soat 10:00 — o'tgan
    await tasks.add_task_time(message, state, db, clock)
    assert await state.get_state() == AddTask.time
    assert "o'tib ketgan" in message.answer.call_args.args[0]


async def test_tomorrow_morning_plan(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Hisobot'), state, db, clock)
    await tasks.add_task_day(make_message('Ertaga'), state, db, clock)
    message = make_message(MORNING)
    await tasks.add_task_time(message, state, db, clock)
    [task] = await db.get_tasks(1)
    assert (task.due_date, task.due_time) == (date(2026, 11, 21), None)
    assert 'ertaga — ertalab 08:00 dagi rejada eslataman' in message.answer.call_args.args[0]


async def test_daily_past_time_starts_tomorrow(db, state, clock, make_message):
    await tasks.add_task_title(make_message('Sport'), state, db, clock)
    await tasks.add_task_day(make_message('🔁 Har kuni'), state, db, clock)
    await tasks.add_task_time(make_message('09:00'), state, db, clock)
    [task] = await db.get_tasks(1)
    assert (task.due_date, task.due_time, task.repeat) == (date(2026, 11, 21), time(9), 'daily')


async def test_edit_due_from_card(db, user, state, clock, make_callback, make_message):
    task_id = await db.add_task(user, 'dars tugedi', TODAY)
    callback = make_callback(user)
    await tasks.task_edit(callback, TaskCallback(action='edit', task_id=task_id), state, db)
    assert await state.get_state() == AddTask.day

    await tasks.add_task_day(make_message('Bugun', user_id=user), state, db, clock)
    message = make_message('18:00', user_id=user)
    await tasks.add_task_time(message, state, db, clock)
    [task] = await db.get_tasks(user)  # yangi vazifa yaratilmadi — o'zi o'zgardi
    assert (task.id, task.due_time) == (task_id, time(18, 0))
    assert "Muddat o'zgartirildi" in message.answer.call_args.args[0]


# --- kengaytirish: bitta xabarda qo'shish, nomni o'zgartirish, sozlamalar ---


@pytest.mark.parametrize(
    ('text', 'title', 'due'),
    [
        ('Hisobot topshirish ertaga 15:00', 'Hisobot topshirish', (date(2026, 11, 21), time(15))),
        ('ertaga 15:00 Hisobot topshirish', 'Hisobot topshirish', (date(2026, 11, 21), time(15))),
        ("Onamga qo'ng'iroq 18:30", "Onamga qo'ng'iroq", (TODAY, time(18, 30))),
    ],
)
async def test_one_message_add(db, state, clock, make_message, text, title, due):
    message = make_message(text)
    await tasks.quick_add(message, state, db, clock)
    assert await state.get_state() is None  # savolsiz saqlandi
    [task] = await db.get_tasks(1)
    assert (task.title, (task.due_date, task.due_time)) == (title, due)
    assert 'aynan shu vaqtda eslataman' in message.answer.call_args.args[0]


async def test_one_message_with_day_asks_only_time(db, state, clock, make_message):
    message = make_message("Kitob o'qish ertaga")
    await tasks.quick_add(message, state, db, clock)
    assert await state.get_state() == AddTask.time
    assert (await state.get_data())['title'] == "Kitob o'qish"


async def test_one_message_past_time_explained(db, state, clock, make_message):
    message = make_message('Hisobot bugun 09:00')  # soat 10:00
    await tasks.quick_add(message, state, db, clock)
    assert "o'tib ketgan" in message.answer.call_args.args[0]
    assert await db.get_tasks(1) == []


async def test_number_inside_title_is_not_due(db, state, clock, make_message):
    await tasks.quick_add(make_message("Python 3.12 o'rnatish"), state, db, clock)
    assert await state.get_state() == AddTask.day
    assert (await state.get_data())['title'] == "Python 3.12 o'rnatish"


async def test_rename_from_card(db, user, state, clock, make_callback, make_message):
    task_id = await db.add_task(user, 'Eski nom')
    callback = make_callback(user)
    await tasks.task_rename(callback, TaskCallback(action='rename', task_id=task_id), state, db)
    await tasks.rename_title(make_message('ab', user_id=user), state, db)  # yaroqsiz
    assert (await db.get_task(task_id, user)).title == 'Eski nom'
    await tasks.rename_title(make_message('Yangi  nom', user_id=user), state, db)
    assert (await db.get_task(task_id, user)).title == 'Yangi nom'
    assert await state.get_state() is None


async def test_settings_change_hour_and_weekly(db, user, state, make_message, make_callback):
    message = make_message(user_id=user)
    await settings.settings_handler(message, state, db, digest_hour=8)
    assert '08:00' in message.answer.call_args.args[0]

    callback = make_callback(user)
    await settings.settings_change(callback, SettingsCallback(action='hour', value=7), db)
    await settings.settings_change(callback, SettingsCallback(action='weekly'), db)
    stored = await db.get_settings(user)
    assert (stored.digest_hour, stored.weekly) == (7, False)
    assert "o'chirilgan" in callback.message.edit_text.call_args.args[0]


async def test_personal_digest_hour_used_in_add_flow(db, user, state, clock, make_message):
    await db.set_digest_hour(user, 10)
    clock.current = datetime(2026, 11, 20, 9, 0)  # umumiy 08:00 o'tgan, shaxsiy 10:00 hali yo'q
    await tasks.quick_add(make_message('Hisobot bugun', user_id=user), state, db, clock)
    message = make_message(MORNING, user_id=user)
    await tasks.add_task_time(message, state, db, clock)
    assert 'ertalab 10:00 dagi rejada' in message.answer.call_args.args[0]
