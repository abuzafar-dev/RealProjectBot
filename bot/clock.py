from datetime import datetime
from zoneinfo import ZoneInfo


class Clock:
    """Foydalanuvchi vaqt zonasidagi joriy vaqt.

    Bazada sana/vaqt shu zonada (zonasiz) saqlanadi. Handlerlarga dependency injection orqali
    beriladi, shuning uchun testlarda vaqtni qotirib qo'yish mumkin.
    """

    def __init__(self, tz: ZoneInfo) -> None:
        self.tz = tz

    def now(self) -> datetime:
        return datetime.now(self.tz).replace(tzinfo=None, second=0, microsecond=0)
