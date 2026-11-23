"""Sozlamalar .env faylidan (yoki muhit o'zgaruvchilaridan) o'qiladi."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    db_path: str
    log_level: str
    timezone: ZoneInfo
    digest_hour: int
    admin_id: int | None = None


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv('BOT_TOKEN', '').strip()
    if not token:
        raise ConfigError(
            'BOT_TOKEN topilmadi. .env faylga @BotFather bergan tokenni yozing '
            '(namuna: .env.example).'
        )
    tz_name = os.getenv('TIMEZONE', 'Asia/Tashkent')
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError(f"TIMEZONE noto'g'ri: {tz_name!r} (masalan: Asia/Tashkent)") from None

    hour = os.getenv('DIGEST_HOUR', '8')
    if not hour.isdigit() or int(hour) > 23:
        raise ConfigError(f"DIGEST_HOUR 0..23 oralig'ida bo'lishi kerak, berilgan: {hour!r}")

    admin = os.getenv('ADMIN_ID', '').strip()
    if admin and not admin.isdigit():
        raise ConfigError(f"ADMIN_ID raqam bo'lishi kerak (Telegram ID), berilgan: {admin!r}")

    return Settings(
        bot_token=token,
        db_path=os.getenv('DB_PATH', 'tasks.db'),
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
        timezone=timezone,
        digest_hour=int(hour),
        admin_id=int(admin) if admin else None,
    )
