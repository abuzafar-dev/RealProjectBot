from datetime import date, datetime, time

import pytest

from bot.due import (
    Due,
    DueParseError,
    format_due,
    morning_reachable,
    next_occurrence,
    parse_due,
    reminder_note,
    resolve_time,
    split_title_due,
    time_options,
)

NOW = datetime(2026, 11, 20, 10, 0)
TODAY = NOW.date()


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('bugun', Due(date(2026, 11, 20))),
        ('Ertaga', Due(date(2026, 11, 21))),
        ('25.11', Due(date(2026, 11, 25))),
        ('5.1', Due(date(2027, 1, 5))),  # yil yozilmagan, sana o'tgan -> keyingi yil
        ('01.03.2027', Due(date(2027, 3, 1))),
        ('ertaga 15:00', Due(date(2026, 11, 21), time(15, 0))),
        ('25.11 9:30', Due(date(2026, 11, 25), time(9, 30))),
        ('18:30', Due(TODAY, time(18, 30))),
    ],
)
def test_parse_due(text, expected):
    assert parse_due(text, NOW) == expected


@pytest.mark.parametrize(
    'text',
    [
        'kecha',
        '',
        'ertaga ertalab',
        'ertaga 9.30',
        '31.02',
        '25:00',
        '09:00',
        '19.11.2026',
        'bugun 09:59',
    ],
)
def test_parse_due_rejects(text):
    with pytest.raises(DueParseError):
        parse_due(text, NOW)


def test_format_due():
    assert format_due(TODAY, time(9, 5), TODAY) == 'bugun 09:05'
    assert format_due(date(2026, 11, 21), None, TODAY) == 'ertaga'
    assert format_due(date(2026, 12, 3), None, TODAY) == '03.12'
    assert format_due(date(2027, 1, 3), None, TODAY) == '03.01.2027'


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('har kuni 18:00', Due(TODAY, time(18, 0), 'daily')),
        ('har kuni 09:00', Due(date(2026, 11, 21), time(9, 0), 'daily')),  # bugungisi o'tgan
        ('Har kuni', Due(TODAY, None, 'daily')),
        ('har hafta 08:00', Due(date(2026, 11, 27), time(8, 0), 'weekly')),
        ('har hafta', Due(TODAY, None, 'weekly')),
    ],
)
def test_parse_repeat(text, expected):
    assert parse_due(text, NOW) == expected


@pytest.mark.parametrize(
    'text',
    ['har', 'har kuni ertalab', 'har kuni 09:00 x', 'har oy 32', 'har oy 5 x', 'har oy 5 9 10'],
)
def test_parse_repeat_rejects(text):
    with pytest.raises(DueParseError):
        parse_due(text, NOW)


def test_next_occurrence_skips_missed_days():
    # 3 kun oldingi vazifa bugun bajarildi — keyingisi o'tmishda emas, kelajakda bo'ladi
    assert next_occurrence(date(2026, 11, 17), time(9, 0), 'daily', NOW) == date(2026, 11, 21)
    assert next_occurrence(date(2026, 11, 17), None, 'daily', NOW) == TODAY
    assert next_occurrence(TODAY, time(18, 0), 'daily', NOW) == date(2026, 11, 21)
    assert next_occurrence(date(2026, 11, 13), time(9, 0), 'weekly', NOW) == date(2026, 11, 27)


def test_format_due_repeat():
    assert format_due(TODAY, time(9, 0), TODAY, 'daily') == 'bugun 09:00 🔁 har kuni'


def test_time_options_today_only_future():
    evening = datetime(2026, 11, 20, 20, 7)
    assert time_options(TODAY, None, evening) == ['⏱ 1 soatdan keyin', '⏱ 3 soatdan keyin', '21:00']
    # boshqa kun yoki takrorlanuvchida barcha soatlar, nisbiy vaqtlarsiz
    assert time_options(date(2026, 11, 21), None, evening) == ['09:00', '13:00', '18:00', '21:00']
    assert time_options(TODAY, 'daily', evening)[0] == '09:00'


def test_morning_reachable():
    assert morning_reachable(TODAY, datetime(2026, 11, 20, 7, 30), 8)
    assert not morning_reachable(TODAY, datetime(2026, 11, 20, 8, 0), 8)
    assert morning_reachable(date(2026, 11, 21), datetime(2026, 11, 20, 23, 0), 8)


def test_resolve_time():
    assert resolve_time(TODAY, time(9, 0), 'weekly', NOW) == date(2026, 11, 27)
    with pytest.raises(DueParseError):
        resolve_time(TODAY, time(9, 0), None, NOW)


def test_reminder_note():
    assert reminder_note(None, None, None, TODAY, 8).startswith('📝 Muddatsiz')
    assert reminder_note(TODAY, time(21), None, TODAY, 8) == (
        '⏰ bugun 21:00 — aynan shu vaqtda eslataman'
    )
    assert reminder_note(date(2026, 11, 21), None, 'daily', TODAY, 8) == (
        '☀️ ertaga 🔁 har kuni — ertalab 08:00 dagi rejada eslataman'
    )


def test_streak():
    from bot.progress import streak

    days = {date(2026, 11, 18), date(2026, 11, 19), date(2026, 11, 20)}
    assert streak(days, TODAY) == 3
    assert streak(days, date(2026, 11, 21)) == 3  # bugun hali bajarmagan — kechadan sanaladi
    assert streak(days, date(2026, 11, 22)) == 0


# 20.11.2026 — juma, 10:00
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('dushanba', Due(date(2026, 11, 23))),
        ('juma 15:00', Due(TODAY, time(15, 0))),  # bugun juma, vaqt hali bor
        ('juma 09:00', Due(date(2026, 11, 27), time(9, 0))),  # bugungisi o'tgan — keyingi hafta
        ('3 kundan keyin', Due(date(2026, 11, 23))),
        ('2 kundan keyin 15:00', Due(date(2026, 11, 22), time(15, 0))),
        ('30 daqiqadan keyin', Due(TODAY, time(10, 30))),
        ('2 soatdan keyin', Due(TODAY, time(12, 0))),
        ('har seshanba 08:30', Due(date(2026, 11, 24), time(8, 30), 'weekly')),
        (
            'ish kunlari 07:00',
            Due(date(2026, 11, 23), time(7, 0), 'weekdays'),
        ),  # shanba o'tkaziladi
    ],
)
def test_parse_weekdays_and_relative(text, expected):
    assert parse_due(text, NOW) == expected


def test_weekdays_repeat_skips_weekend():
    assert next_occurrence(TODAY, time(7, 0), 'weekdays', NOW) == date(2026, 11, 23)


@pytest.mark.parametrize(
    ('text', 'title'),
    [
        ('Juma namozi', 'Juma namozi'),  # boshidagi yolg'iz kun nomi — nomning bir qismi
        ('Shanba kuni bozor', 'Shanba kuni bozor'),
        ('Bozor shanba', 'Bozor'),
        ('juma 12:30 Namoz', 'Namoz'),
        ('Dori 2 soatdan keyin', 'Dori'),
        ('Uchrashuv 2 kundan keyin 15:00', 'Uchrashuv'),
    ],
)
def test_split_weekday_edge_cases(text, title):
    assert split_title_due(text, NOW)[0] == title


def test_format_weekly_shows_weekday():
    assert format_due(date(2026, 11, 24), time(8, 30), TODAY, 'weekly') == (
        '24.11 08:30 🔁 har seshanba'
    )


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('har oy', Due(TODAY, None, 'monthly:20')),
        ('har oy 25', Due(date(2026, 11, 25), None, 'monthly:25')),
        ('har oy 5 10:00', Due(date(2026, 12, 5), time(10, 0), 'monthly:5')),  # bu oyniki o'tgan
        (
            'har oy 20 09:00',
            Due(date(2026, 12, 20), time(9, 0), 'monthly:20'),
        ),  # bugun, vaqt o'tgan
        ('har oy 31', Due(date(2026, 11, 30), None, 'monthly:31')),  # noyabrda 31 yo'q
    ],
)
def test_parse_monthly(text, expected):
    assert parse_due(text, NOW) == expected


def test_monthly_keeps_original_day():
    # 31-yanvar -> 28-fevral -> 31-mart: qisqa oydan keyin asl kunga qaytadi
    later = datetime(2027, 1, 31, 12, 0)
    day = next_occurrence(date(2027, 1, 31), None, 'monthly:31', later)
    assert day == date(2027, 2, 28)
    assert next_occurrence(day, None, 'monthly:31', later) == date(2027, 3, 31)
    assert next_occurrence(date(2026, 12, 15), None, 'monthly:15', NOW) == date(2027, 1, 15)
    assert (
        format_due(date(2026, 12, 5), time(10, 0), TODAY, 'monthly:5')
        == '05.12 10:00 🔁 har oy 5-kuni'
    )


def test_split_monthly():
    title, due = split_title_due("Ijara to'lash har oy 5 10:00", NOW)
    assert title == "Ijara to'lash"
    assert due == Due(date(2026, 12, 5), time(10, 0), 'monthly:5')
