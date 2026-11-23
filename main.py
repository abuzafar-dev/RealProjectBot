import asyncio
import contextlib
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand
from aiogram.utils.token import TokenValidationError

from bot.clock import Clock
from bot.config import ConfigError, load_settings
from bot.database import Database
from bot.handlers import get_router
from bot.reminders import run_reminders
from bot.texts import DESCRIPTION, SHORT_DESCRIPTION

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command='start', description='Bosh menyu'),
    BotCommand(command='today', description='Bugungi reja'),
    BotCommand(command='help', description='Yordam'),
    BotCommand(command='cancel', description='Bekor qilish'),
]


async def setup_profile(bot: Bot) -> None:
    """Menyu buyruqlari va Start'dan oldin ko'rinadigan tavsif. Faqat o'zgargan bo'lsa yoziladi."""
    await bot.set_my_commands(COMMANDS)
    if (await bot.get_my_description()).description != DESCRIPTION:
        await bot.set_my_description(DESCRIPTION)
        logger.info('Bot tavsifi yangilandi')
    if (await bot.get_my_short_description()).short_description != SHORT_DESCRIPTION:
        await bot.set_my_short_description(SHORT_DESCRIPTION)
        logger.info('Bot qisqa tavsifi yangilandi')


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
    clock = Clock(settings.timezone)
    # db va clock handlerlarga argument sifatida avtomatik uzatiladi (dependency injection)
    dp = Dispatcher(db=db, clock=clock, admin_id=settings.admin_id)
    dp.include_router(get_router())

    reminders = asyncio.create_task(run_reminders(bot, db, clock, settings.digest_hour))
    try:
        await setup_profile(bot)
        await dp.start_polling(bot)
    finally:
        reminders.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminders
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
