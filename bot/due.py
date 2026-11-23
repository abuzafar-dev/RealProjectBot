"""Muddatni matndan o'qish va chiroyli ko'rsatish (sof funksiyalar, test qilish oson).

Qabul qilinadigan formatlar:
    bugun | ertaga | 25.11 | 25.11.2026      — faqat sana (ertalabki rejaga tushadi)
    ... 15:00                                 — sana + vaqt (shu vaqtda eslatma keladi)
    15:00                                     — bugun, shu vaqtda
    har kuni [09:00] | har hafta [09:00]      — takrorlanuvchi vazifa
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

_TIME_RE = re.compile(r'^(\d{1,2}):(\d{2})$')
_DATE_RE = re.compile(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$')


class DueParseError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan xabar bilan."""


@dataclass(frozen=True, slots=True)
class Due:
    day: date
    at: time | None = None
    repeat: str | None = None  # 'daily' | 'weekly'


REPEATS = {'kuni': 'daily', 'hafta': 'weekly'}
REPEAT_STEP = {'daily': timedelta(days=1), 'weekly': timedelta(days=7)}
REPEAT_LABEL = {'daily': 'har kuni', 'weekly': 'har hafta'}


def _parse_time(text: str) -> time | None:
    match = _TIME_RE.match(text)
    if not match:
        return None
    hour, minute = int(match[1]), int(match[2])
    if hour > 23 or minute > 59:
        raise DueParseError("Vaqt noto'g'ri. Masalan: 09:30 yoki 18:00")
    return time(hour, minute)


def _parse_day(text: str, today: date) -> date | None:
    if text == 'bugun':
        return today
    if text == 'ertaga':
        return today + timedelta(days=1)
    match = _DATE_RE.match(text)
    if not match:
        return None
    day, month = int(match[1]), int(match[2])
    year = int(match[3]) if match[3] else today.year
    try:
        result = date(year, month, day)
    except ValueError:
        raise DueParseError("Bunday sana yo'q. Masalan: 25.11 yoki 25.11.2026") from None
    # Yil yozilmagan va sana o'tib ketgan bo'lsa — keyingi yil (31.12 da "05.01" deganda)
    if not match[3] and result < today:
        result = result.replace(year=year + 1)
    return result


def _is_past(day: date, at: time | None, now: datetime) -> bool:
    if at is None:
        return day < now.date()
    return datetime.combine(day, at) <= now.replace(tzinfo=None)


def _parse_repeat(parts: list[str], now: datetime) -> Due:
    repeat = REPEATS.get(parts[1]) if len(parts) > 1 else None
    if repeat is None or len(parts) > 3:
        raise DueParseError(FORMAT_HINT)
    at = _parse_time(parts[2]) if len(parts) == 3 else None
    if len(parts) == 3 and at is None:
        raise DueParseError(FORMAT_HINT)
    day = now.date()
    if _is_past(day, at, now):  # bugungi vaqt o'tib ketgan — birinchisi keyingi takrorda
        day += REPEAT_STEP[repeat]
    return Due(day, at, repeat)


def next_occurrence(day: date, at: time | None, repeat: str, now: datetime) -> date:
    """Takrorlanuvchi vazifaning keyingi sanasi — har doim kelajakda (o'tgan kunlar o'tkaziladi)."""
    step = REPEAT_STEP[repeat]
    day += step
    while _is_past(day, at, now):
        day += step
    return day


def parse_due(text: str, now: datetime) -> Due:
    parts = text.strip().lower().split()
    if parts and parts[0] == 'har':
        return _parse_repeat(parts, now)
    if not 1 <= len(parts) <= 2:
        raise DueParseError(FORMAT_HINT)

    today = now.date()
    at = _parse_time(parts[-1])
    if len(parts) == 1 and at is not None:
        day = today
    else:
        day = _parse_day(parts[0], today)
        if day is None or (len(parts) == 2 and at is None):
            raise DueParseError(FORMAT_HINT)

    if day < today:
        raise DueParseError("Bu sana o'tib ketgan. Bugungi yoki keyingi sanani yozing")
    if at is not None and _is_past(day, at, now):
        raise DueParseError("Bu vaqt o'tib ketgan. Keyinroq vaqtni yozing")
    return Due(day, at)


FORMAT_HINT = (
    'Muddatni tushunmadim. Masalan:\n'
    '<code>ertaga</code>, <code>25.11</code>, <code>ertaga 15:00</code>, <code>18:30</code>, '
    '<code>har kuni 09:00</code>, <code>har hafta</code>'
)


def format_due(day: date, at: time | None, today: date, repeat: str | None = None) -> str:
    if day == today:
        label = 'bugun'
    elif day == today + timedelta(days=1):
        label = 'ertaga'
    elif day == today - timedelta(days=1):
        label = 'kecha'
    else:
        label = day.strftime('%d.%m') if day.year == today.year else day.strftime('%d.%m.%Y')
    text = f'{label} {at:%H:%M}' if at else label
    return f'{text} 🔁 {REPEAT_LABEL[repeat]}' if repeat else text
