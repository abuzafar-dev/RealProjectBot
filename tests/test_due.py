from datetime import date, datetime, time

import pytest

from bot.due import Due, DueParseError, format_due, parse_due

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
