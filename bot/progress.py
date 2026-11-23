"""Ketma-ketlik (streak) va haftalik hisobot — sof funksiyalar."""

from datetime import date, timedelta

from bot.database import WeekSummary

WEEKLY_DAY = 6  # yakshanba (date.weekday())
WEEKLY_HOUR = 20


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def streak(done_days: set[date], today: date) -> int:
    """Ketma-ket necha kun vazifa bajarilgan (bugun hali bo'lmasa — kechadan sanaladi)."""
    day = today if today in done_days else today - timedelta(days=1)
    count = 0
    while day in done_days:
        count += 1
        day -= timedelta(days=1)
    return count


def streak_text(days: int) -> str:
    return f'🔥 {days} kun ketma-ket' if days else '🔥 Bugun boshlang — ketma-ketlik 0'


def weekly_text(summary: WeekSummary, days: int, today: date) -> str:
    start = week_start(today)
    if summary.done >= 10:
        cheer = "Zo'r hafta bo'ldi! 💪"
    elif summary.done:
        cheer = 'Yaxshi natija, davom eting! 👏'
    else:
        cheer = "Bu hafta bajarilgan vazifa yo'q — keyingisini kichik ishdan boshlang 🙂"
    lines = [
        f'📈 <b>Haftalik hisobot</b> ({start:%d.%m}–{today:%d.%m})',
        '',
        f'✅ Bajarildi: {summary.done} ta',
        f"⚠️ Muddati o'tgan: {summary.overdue} ta",
        streak_text(days),
        f'🗓 Keyingi 7 kunga: {summary.planned} ta',
        '',
        cheer,
    ]
    return '\n'.join(lines)
