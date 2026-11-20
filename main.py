import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand
from aiogram.utils.token import TokenValidationError

from bot.config import ConfigError, load_settings
from bot.database import Database
from bot.handlers import get_router

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command='start', description='Bosh menyu'),
    BotCommand(command='help', description='Yordam'),
    BotCommand(command='cancel', description='Bekor qilish'),
]


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    db = Database(settings.db_path)
    await db.connect()
    logger.info('Baza ulandi: %s', settings.db_path)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # db handlerlarga argument sifatida avtomatik uzatiladi (dependency injection)
    dp = Dispatcher(db=db)
    dp.include_router(get_router())

    try:
        await bot.set_my_commands(COMMANDS)
        await dp.start_polling(bot)
    finally:
        await db.close()
        logger.info("Bot to'xtatildi")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except ConfigError as error:
        sys.exit(f'XATO: {error}')
    except (TokenValidationError, TelegramUnauthorizedError):
        sys.exit("XATO: BOT_TOKEN noto'g'ri. @BotFather'dan tokenni qayta nusxalang.")
    except KeyboardInterrupt:
        pass
