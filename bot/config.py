"""Sozlamalar .env faylidan (yoki muhit o'zgaruvchilaridan) o'qiladi."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    db_path: str
    log_level: str


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv('BOT_TOKEN', '').strip()
    if not token:
        raise ConfigError(
            'BOT_TOKEN topilmadi. .env faylga @BotFather bergan tokenni yozing '
            '(namuna: .env.example).'
        )
    return Settings(
        bot_token=token,
        db_path=os.getenv('DB_PATH', 'tasks.db'),
        log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    )
